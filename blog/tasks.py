import os
import logging

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


def _auto_fill_post_refund(instance):
    """A negative Stripe/PayPal payment (refund) matched to exactly one Post
    whose refund field is still empty gets that Post.refund auto-filled, so
    the admin doesn't have to type it in by hand. If Post.refund is already
    set (manually entered) or the match is ambiguous (0 or 2+ posts), leave
    it alone — accounting (BAS 1A netting) relies on Post.refund being
    correct, so we only auto-fill when there's a single unambiguous match.
    Returns the Post if it was auto-filled, else None, and the match count."""
    from .blog_utils import match_posts_for_payer

    matched_posts = match_posts_for_payer(instance)
    match_count = matched_posts.count()
    if match_count != 1:
        return None, match_count

    post = matched_posts.first()
    if post.refund:
        return None, match_count

    post.refund = abs(instance.amount)
    post.save(update_fields=['refund'])
    return post, match_count


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
                auto_filled_post, match_count = _auto_fill_post_refund(instance)
                send_refund_notification_email(
                    instance, method="PAYPAL", amount=raw_amount,
                    auto_filled_post=auto_filled_post, match_count=match_count,
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
            auto_filled_post, match_count = _auto_fill_post_refund(instance)
            send_refund_notification_email(
                instance, method="STRIPE", amount=raw_amount,
                auto_filled_post=auto_filled_post, match_count=match_count,
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


