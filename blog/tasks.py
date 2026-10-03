import os
import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from celery import shared_task

from main import settings
from main.settings import RECIPIENT_EMAIL
from .models import Inquiry, Post, PaypalPayment, StripePayment
from utils.inquiry_helper import send_inquiry_email
from utils.post_helper import send_missing_direction_email, send_post_cancelled_email, send_post_confirmation_email


logger = logging.getLogger('easygo')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _return_pair(posts):
    """The two legs of one return booking, earlier leg first, or None.

    The first leg's return_pickup_date is the second leg's pickup_date."""
    if len(posts) != 2:
        return None
    first, second = sorted(posts, key=lambda p: (p.pickup_date or date.min, p.pk))
    if first.return_pickup_date and first.return_pickup_date == second.pickup_date:
        return first, second
    return None


def _paid_decimal(post):
    try:
        return Decimal(str(post.paid or '0').replace('$', '').replace(',', '').strip())
    except Exception:
        return Decimal('0')


def _auto_fill_post_refund(instance):
    """A negative Stripe/PayPal payment (refund) matched to exactly one Post
    whose refund field is still empty gets that Post.refund auto-filled, so
    the admin doesn't have to type it in by hand. A return booking (two legs
    matched) is filled on the later leg; whatever exceeds that leg's paid
    spills onto the earlier leg, since BAS netting drops a refund above paid.
    If Post.refund is already set (manually entered) or the match is otherwise
    ambiguous, leave it alone — accounting (BAS 1A netting) relies on
    Post.refund being correct.
    Returns the list of (Post, amount) filled (empty if none) and the match count."""
    from .blog_utils import match_posts_for_payer

    matched_posts = list(match_posts_for_payer(instance))
    match_count = len(matched_posts)
    if match_count == 1:
        legs = matched_posts
    else:
        pair = _return_pair(matched_posts)
        if pair is None:
            return [], match_count
        legs = [pair[1], pair[0]]   # later leg first

    if any(post.refund for post in legs):
        return [], match_count

    refund = abs(instance.amount)
    if isinstance(instance, PaypalPayment):
        # Post.paid holds PayPal payments ex the 3% surcharge (amount / 1.03),
        # so store the refund on the same basis. The surcharge portion of the
        # refund is netted in accounting.reports.paypal_surcharge_total.
        refund = (refund / Decimal('1.03')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    filled = []
    remaining = refund
    for i, post in enumerate(legs):
        last = i == len(legs) - 1
        amount = remaining if last else min(remaining, _paid_decimal(post))
        if amount <= 0:
            continue
        # 환불 메일이 이미 나가므로 sent_email 부터 먼저 저장해 취소 메일을 막는다.
        post.refund = amount
        post.sent_email = True
        post.save(update_fields=['refund', 'sent_email'])
        # 전액 환불만 취소 처리한다. 부분 환불은 운행이 남아 있으므로 리뷰 요청만 막는다.
        paid = _paid_decimal(post)
        fields = []
        if paid > 0 and amount >= paid:
            post.cancelled = True
            fields.append('cancelled')
        post.no_review = True
        fields.append('no_review')
        post.save(update_fields=fields)
        filled.append((post, amount))
        remaining -= amount
    return filled, match_count


# Google Calendar event 
@shared_task
def create_event_on_calendar(instance_id):
    if settings.DEBUG:
        return
    from utils.calendar_sync import sync_to_calendar    
    try:
        instance = Post.objects.get(pk=instance_id)
    except Post.DoesNotExist:
        logger.warning(f"Post with id {instance_id} does not exist.")
        return 

    event_id = (instance.calendar_event_id or '').strip()

    if instance.cancelled and not event_id:
        logger.info(f"Cancelled post {instance_id} with no event_id. Skipping event creation.")
        return

    # ✅ 회사 캘린더 (기존)
    sync_to_calendar(instance)

    # ✅ 드라이버 캘린더 (추가)
    if instance.driver and getattr(instance.driver, 'google_calendar_id', None):
        sync_to_calendar(instance, calendar_id=instance.driver.google_calendar_id, is_driver=True)


# PayPal payment in tasks.py
@shared_task
def notify_user_payment_paypal(instance_id):
    from .blog_utils import (
        handle_paypal_dispute, handle_paypal_dispute_resolved,
        process_generic_payment, send_payment_notification_email, send_refund_notification_email,
    )
    with transaction.atomic():
        try:
            instance = PaypalPayment.objects.select_for_update().get(id=instance_id)
        except PaypalPayment.DoesNotExist:
            return

        raw_amount = float(instance.amount or 0)
        kind = instance.kind

        # Anything that is not money coming in is handled here and returns: a
        # dispute must not send the customer a refund email, and a dispute being
        # reversed back must not be booked as a fresh payment.
        if kind != PaypalPayment.KIND_PAYMENT:
            if instance.is_processed:
                return
            instance.is_processed = True
            instance.processed_at = timezone.now()
            instance.save()

            if kind == PaypalPayment.KIND_DISPUTE:
                handle_paypal_dispute(instance, method="PAYPAL")
            elif kind == PaypalPayment.KIND_DISPUTE_RESOLVED:
                handle_paypal_dispute_resolved(instance, method="PAYPAL")
            else:
                auto_filled, match_count = _auto_fill_post_refund(instance)
                send_refund_notification_email(
                    instance, method="PAYPAL", amount=raw_amount,
                    auto_filled=auto_filled, match_count=match_count,
                )
            return

        calculated_amount = round(raw_amount / 1.03, 2)

        posts = Post.objects.filter(
            Q(booker_email__iexact=instance.email) |
            Q(email__iexact=instance.email) |
            Q(name__iexact=instance.name)
        ).order_by('pickup_date')

        success, total_balance, recipient_emails, has_future_bookings, all_already_paid, deposit_satisfied = process_generic_payment(
            instance, posts, RECIPIENT_EMAIL, calculated_amount
        )
        first_post = posts.first()
        booker_name = first_post.booker_name if first_post else None
        booker_contact = first_post.booker_contact if first_post else None
        nearest_future_post = posts.filter(
            pickup_date__isnull=False,
            pickup_date__gte=timezone.localdate(),
        ).first()
        prepay_qs = posts.filter(prepay=True, pickup_date__gte=timezone.localdate()).order_by('-id')
        prepay_post = prepay_qs.first()
        if prepay_post and prepay_post.return_pickup_time == 'x':
            prepay_post = prepay_qs[1:2].first()

        if not success: return

    send_payment_notification_email(
        instance, total_balance, recipient_emails, RECIPIENT_EMAIL,
        method="PAYPAL",
        raw_amount=raw_amount,
        net_amount=calculated_amount,
        booker_name=booker_name,
        booker_contact=booker_contact,
        has_future_bookings=has_future_bookings,
        all_already_paid=all_already_paid,
        nearest_post=nearest_future_post,
        deposit_satisfied=deposit_satisfied,
    )

    if prepay_post and not (prepay_post.company_name or '').strip():
        send_post_confirmation_email_task.delay(prepay_post.pk)


# Stripe payment
@shared_task
def notify_user_payment_stripe(instance_id):
    from .blog_utils import process_generic_payment, send_payment_notification_email, send_refund_notification_email
    with transaction.atomic():
        try:
            instance = StripePayment.objects.select_for_update().get(id=instance_id)
        except StripePayment.DoesNotExist:
            return

        raw_amount = float(instance.amount or 0)

        if raw_amount < 0:
            if instance.is_processed:
                return
            instance.is_processed = True
            instance.processed_at = timezone.now()
            instance.save()
            auto_filled, match_count = _auto_fill_post_refund(instance)
            send_refund_notification_email(
                instance, method="STRIPE", amount=raw_amount,
                auto_filled=auto_filled, match_count=match_count,
            )
            return

        posts = Post.objects.filter(
            Q(booker_email__iexact=instance.email) |
            Q(email__iexact=instance.email) |
            Q(name__iexact=instance.name)
        ).order_by('pickup_date')

        success, total_balance, recipient_emails, has_future_bookings, all_already_paid, deposit_satisfied = process_generic_payment(instance, posts, RECIPIENT_EMAIL)
        first_post = posts.first()
        booker_name = first_post.booker_name if first_post else None
        booker_contact = first_post.booker_contact if first_post else None
        nearest_future_post = posts.filter(
            pickup_date__isnull=False,
            pickup_date__gte=timezone.localdate(),
        ).first()
        prepay_qs = posts.filter(prepay=True, pickup_date__gte=timezone.localdate()).order_by('-id')
        prepay_post = prepay_qs.first()
        if prepay_post and prepay_post.return_pickup_time == 'x':
            prepay_post = prepay_qs[1:2].first()

        if not success: return

    send_payment_notification_email(
        instance, total_balance, recipient_emails, RECIPIENT_EMAIL,
        method="STRIPE",
        booker_name=booker_name,
        booker_contact=booker_contact,
        has_future_bookings=has_future_bookings,
        all_already_paid=all_already_paid,
        nearest_post=nearest_future_post,
        deposit_satisfied=deposit_satisfied,
    )

    if prepay_post and not (prepay_post.company_name or '').strip():
        send_post_confirmation_email_task.delay(prepay_post.pk)


@shared_task
def send_post_confirmation_email_task(pk):
    affected = Post.objects.filter(
        pk=pk,
        sent_email=False,
    ).update(sent_email=True)
    
    if affected:
        instance = Post.objects.get(pk=pk)
        send_post_confirmation_email(instance)


@shared_task
def send_post_cancelled_email_task(pk):
    affected = Post.objects.filter(
        pk=pk,
        sent_email=False,
        cancelled=True
    ).update(sent_email=True)
    
    if affected:
        instance = Post.objects.get(pk=pk)
        send_post_cancelled_email(instance)


@shared_task
def send_missing_direction_email_task(pk):
    try:
        instance = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        logger.warning(f"Post {pk} does not exist.")
        return
    send_missing_direction_email(instance)


@shared_task
def check_and_send_missing_info_email_task(pk):
    from basecamp.basecamp_utils import check_and_send_missing_info_email
    try:
        instance = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        logger.warning(f"Post {pk} does not exist.")
        return
    check_and_send_missing_info_email(instance)


@shared_task
def send_inquiry_email_task(pk):
    affected = Inquiry.objects.filter(
        pk=pk,
        sent_email=False,
    ).filter(
        Q(is_confirmed=True) | Q(cancelled=True) | Q(pending=True)
    ).update(sent_email=True)

    if affected:
        instance = Inquiry.objects.get(pk=pk)
        send_inquiry_email(instance)


