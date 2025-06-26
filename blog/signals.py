from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from utils.email_helper import EmailSender
from main.settings import RECIPIENT_EMAIL

from .models import Post, Inquiry, PaypalPayment, StripePayment
from .tasks import create_event_on_calendar, notify_user_payment_paypal, notify_user_payment_stripe
from utils.return_booking import handle_return_trip
from utils.inquiry_helper import send_inquiry_email  
from utils.post_helper import send_post_cancelled_email, send_missing_direction_email


@receiver(post_save, sender=Inquiry, dispatch_uid="notify_user_inquiry_once")
def notify_user_inquiry(sender, instance, created, **kwargs):
    send_inquiry_email(instance)


@receiver(post_save, sender=Post, dispatch_uid="notify_user_post_once")
def notify_user_post(sender, instance, created, **kwargs):
    handle_return_trip(instance)


@receiver(post_save, sender=Post, dispatch_uid="notify_user_post_cancelled_once")
def notify_user_post_cancelled(sender, instance, created, **kwargs): 
    if not created and instance.cancelled and not instance.sent_email:
        send_post_cancelled_email(instance)
        instance.sent_email = True
        instance.save(update_fields=['sent_email'])

    
@receiver(post_save, sender=PaypalPayment, dispatch_uid="async_notify_user_payment_paypal_once")
def async_notify_user_payment_paypal(sender, instance, created, **kwargs):
    if created:
        notify_user_payment_paypal.delay(instance.id)


@receiver(post_save, sender=StripePayment, dispatch_uid="async_notify_user_payment_stripe_once")
def async_notify_user_payment_stripe(sender, instance, created, **kwargs):
    if created:
        notify_user_payment_stripe.delay(instance.id)


## google calendar recording 
@receiver(post_save, sender=Post, dispatch_uid="async_create_event_on_calendar_once")
def async_create_event_on_calendar(sender, instance, created, **kwargs):
    create_event_on_calendar.delay(instance.id)


# check missing direction when flight number exists
@receiver(post_save, sender=Post, dispatch_uid="check_missing_direction_once")
def check_missing_direction(sender, instance, created, **kwargs):
    if created and instance.flight_number and not (instance.direction and instance.direction.strip()):
        send_missing_direction_email(instance)

                