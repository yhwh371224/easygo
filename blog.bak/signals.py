import re

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from utils.email_helper import EmailSender
from main.settings import RECIPIENT_EMAIL

from .models import Post, Inquiry, PaypalPayment, StripePayment
from .tasks import create_event_on_calendar, notify_user_payment_paypal, notify_user_payment_stripe
from basecamp.utils import check_and_send_missing_info_email
from utils.return_booking import handle_return_trip
from utils.inquiry_helper import send_inquiry_email  
from utils.prepay_helper import is_foreign_number
from utils.post_helper import send_post_confirmation_email, send_post_cancelled_email, send_missing_direction_email


# Inquiry signals
@receiver(post_save, sender=Inquiry, dispatch_uid="notify_user_inquiry_once")
def notify_user_inquiry(sender, instance, created, **kwargs):
    send_inquiry_email(instance)


# Post signals
@receiver(post_save, sender=Post, dispatch_uid="notify_user_post_once")
def notify_user_post(sender, instance, created, **kwargs):
    handle_return_trip(instance)

    update_fields = []

    # price 처리
    if instance.price in [None, ""]:
        instance.price = "TBA"
        update_fields.append('price')

    # ✅ paid 값이 있으면 cash = False
    if instance.paid not in [None, ""] and instance.cash:
        instance.cash = False
        update_fields.append('cash')

    if instance.is_confirmed and not instance.sent_email:
        send_post_confirmation_email(instance)
        instance.sent_email = True
        update_fields.append('sent_email')

        if not instance.cash and not instance.paid:
            instance.pending = True
            update_fields.append('pending')

    if update_fields:
        instance.save(update_fields=update_fields)


# Send email notification if a Post is cancelled and email hasn't been sent yet
@receiver(post_save, sender=Post, dispatch_uid="notify_user_post_cancelled_once")
def notify_user_post_cancelled(sender, instance, created, **kwargs): 
    if instance.cancelled and not instance.sent_email:
        send_post_cancelled_email(instance)
        instance.sent_email = True  
        instance.save(update_fields=['sent_email'])


# Automatically set prepay to True for foreign contacts or company names
@receiver(post_save, sender=Post, dispatch_uid="set_prepay_for_foreign_users")
def set_prepay_for_foreign_users(sender, instance, created, **kwargs):
    if not instance.pk or instance.cash:        
        return  # Skip if not saved properly

    if not instance.prepay: 
        if is_foreign_number(instance.contact) or (instance.company_name or "").strip():
            Post.objects.filter(pk=instance.pk).update(prepay=True)


# Payment signals (Paypal)   
@receiver(post_save, sender=PaypalPayment, dispatch_uid="async_notify_user_payment_paypal_once")
def async_notify_user_payment_paypal(sender, instance, created, **kwargs):
    if created:
        notify_user_payment_paypal.delay(instance.id)


# Payment signals (Stripe)
@receiver(post_save, sender=StripePayment, dispatch_uid="async_notify_user_payment_stripe_once")
def async_notify_user_payment_stripe(sender, instance, created, **kwargs):
    if created:
        notify_user_payment_stripe.delay(instance.id)


# google calendar recording 
@receiver(post_save, sender=Post, dispatch_uid="async_create_event_on_calendar_once")
def async_create_event_on_calendar(sender, instance, created, **kwargs):
    create_event_on_calendar.delay(instance.id)


# check missing direction when flight number exists
@receiver(post_save, sender=Post, dispatch_uid="check_missing_direction_once")
def check_missing_direction(sender, instance, created, **kwargs):
    if created and instance.flight_number and not (instance.direction and instance.direction.strip()):
        send_missing_direction_email(instance)


# check missing flight contact info
@receiver(post_save, sender=Post, dispatch_uid="check_missing_flight_contact_once")
def check_missing_flight_contact(sender, instance, created, **kwargs):
    if created:
        check_and_send_missing_info_email(instance)                