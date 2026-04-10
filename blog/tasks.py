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

    sync_to_calendar(instance)


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
        
        if not success: return

    send_payment_notification_email(
        instance, total_balance, recipient_emails, RECIPIENT_EMAIL,
        method="PAYPAL",
        raw_amount=raw_amount,
        net_amount=calculated_amount
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
            Q(email__iexact=instance.email) | 
            Q(name__iexact=instance.name)
        ).order_by('pickup_date')

        success, total_balance, recipient_emails = process_generic_payment(instance, posts, RECIPIENT_EMAIL)
       
        if not success: return 
    
    send_payment_notification_email(
        instance, total_balance, recipient_emails, RECIPIENT_EMAIL, 
        method="STRIPE"
    )


@shared_task
def send_post_confirmation_email_task(pk):
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
    instance = Post.objects.get(pk=pk)
    send_missing_direction_email(instance)


@shared_task
def check_and_send_missing_info_email_task(pk):
    from basecamp.basecamp_utils import check_and_send_missing_info_email
    instance = Post.objects.get(pk=pk)
    check_and_send_missing_info_email(instance)


@shared_task
def send_inquiry_email_task(pk):
    instance = Inquiry.objects.get(pk=pk)
    if send_inquiry_email(instance):
        Inquiry.objects.filter(pk=pk).update(sent_email=True)

            
# XRP payment record and email
# @shared_task
# def send_xrp_internal_email(subject, message, from_email, recipient_list):
#     """회사 내부 알림(텍스트)"""
#     send_text_email(subject, message, recipient_list, from_email=from_email)

# @shared_task
# def send_xrp_customer_email(email: str, xrp_amount: str, xrp_address: str, dest_tag: int):
#     """
#     고객에게 XRP 결제 안내 메일 전송 (HTML, 이름 없음)
#     QR 코드 기능 제거 버전
#     """
#     context = {
#         "email": email,
#         "amount": f"{Decimal(xrp_amount):.2f} XRP",
#         "address": xrp_address,
#         "dest_tag": dest_tag,
#     }

#     html_content = render_email_template("html_email-xrppayment.html", context)

#     try:
#         send_html_email("XRP Payment - EasyGo", html_content, [email], from_email=RECIPIENT_EMAIL)
#     except Exception as e:
#         logger.exception("Failed to send XRP payment email: %s", e)





