import os
import logging

from django.db import transaction
from django.db.models import Q

from celery import shared_task

from main.settings import RECIPIENT_EMAIL
from .models import Inquiry, Post, PaypalPayment, StripePayment
from utils.inquiry_helper import send_inquiry_email
from utils.post_helper import send_missing_direction_email, send_post_cancelled_email, send_post_confirmation_email


logger = logging.getLogger('easygo')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Google Calendar event 
@shared_task
def create_event_on_calendar(instance_id):
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
    from .blog_utils import process_generic_payment, send_payment_notification_email
    with transaction.atomic():
        try:
            instance = PaypalPayment.objects.select_for_update().get(id=instance_id)
        except PaypalPayment.DoesNotExist:
            return
        
        raw_amount = float(instance.amount or 0)
        calculated_amount = round(raw_amount / 1.03, 2)

        posts = Post.objects.filter(
            Q(booker_email__iexact=instance.email) |
            Q(email__iexact=instance.email) | 
            Q(name__iexact=instance.name)
        ).order_by('pickup_date')
        
        success, total_balance, recipient_emails = process_generic_payment(
            instance, posts, RECIPIENT_EMAIL, calculated_amount
        )
        first_post = posts.first()
        booker_name = first_post.booker_name if first_post else None

        if not success: return

    send_payment_notification_email(
        instance, total_balance, recipient_emails, RECIPIENT_EMAIL,
        method="PAYPAL",
        raw_amount=raw_amount,
        net_amount=calculated_amount,
        booker_name=booker_name,
    )


# Stripe payment 
@shared_task
def notify_user_payment_stripe(instance_id):
    from .blog_utils import process_generic_payment, send_payment_notification_email
    with transaction.atomic():
        try:
            instance = StripePayment.objects.select_for_update().get(id=instance_id)
        except StripePayment.DoesNotExist:
            return

        posts = Post.objects.filter(
            Q(booker_email__iexact=instance.email) |
            Q(email__iexact=instance.email) |
            Q(name__iexact=instance.name)
        ).order_by('pickup_date')

        success, total_balance, recipient_emails = process_generic_payment(instance, posts, RECIPIENT_EMAIL)
        first_post = posts.first()
        booker_name = first_post.booker_name if first_post else None

        if not success: return

    send_payment_notification_email(
        instance, total_balance, recipient_emails, RECIPIENT_EMAIL,
        method="STRIPE",
        booker_name=booker_name,
    )


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


