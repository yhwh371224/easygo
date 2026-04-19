import logging
from django.db.models.signals import post_save, pre_save
from django.db import transaction
from django.dispatch import receiver
from django.core.management import call_command

from .models import Post, Inquiry, PaypalPayment, StripePayment
from .tasks import (
    create_event_on_calendar,
    notify_user_payment_paypal,
    notify_user_payment_stripe,
    send_post_confirmation_email_task,
    send_post_cancelled_email_task,
    send_missing_direction_email_task,
    check_and_send_missing_info_email_task,
    send_inquiry_email_task,
)

from utils.return_booking import handle_return_trip
from utils.prepay_helper import is_foreign_number

logger = logging.getLogger('easygo')


# Inquiry signals
@receiver(post_save, sender=Inquiry, dispatch_uid="notify_user_inquiry_once")
def notify_user_inquiry(sender, instance, created, **kwargs):
    if not instance.sent_email:
        pk = instance.pk
        transaction.on_commit(lambda: send_inquiry_email_task.delay(pk))


# Post signals
@receiver(post_save, sender=Post, dispatch_uid="notify_user_post_once")
def notify_user_post(sender, instance, created, **kwargs):
    handle_return_trip(instance)

    update_data = {}

    # price 처리
    if instance.price in [None, ""]:
        update_data['price'] = "TBA"

    # 이메일 조건
    if not instance.cash and not instance.paid:
        update_data['pending'] = True

    if instance.is_confirmed:
        pk = instance.pk
        transaction.on_commit(
            lambda: send_post_confirmation_email_task.delay(pk)
        )

    if update_data:
        Post.objects.filter(pk=instance.pk).update(**update_data)


# Send email notification if a Post is cancelled and email hasn't been sent yet
@receiver(post_save, sender=Post, dispatch_uid="notify_user_post_cancelled_once")
def notify_user_post_cancelled(sender, instance, created, **kwargs):
    update_fields = kwargs.get('update_fields')
    
    # 뷰에서 update_fields=['cancelled', 'pending']으로 저장한 경우 → 시그널 스킵
    if update_fields and 'cancelled' in update_fields:
        return
    
    if instance.sent_email:
        return
    
    if instance.cancelled:
        pk = instance.pk
        transaction.on_commit(lambda: send_post_cancelled_email_task.delay(pk))
        

# Automatically set prepay to True for foreign contacts or company names
@receiver(post_save, sender=Post, dispatch_uid="set_prepay_for_foreign_users")
def set_prepay_for_foreign_users(sender, instance, created, **kwargs):
    if not instance.pk or instance.cash:        
        return  

    if not instance.prepay: 
        if is_foreign_number(instance.contact) or (instance.company_name or "").strip():
            Post.objects.filter(pk=instance.pk).update(prepay=True)


# Payment signals (Paypal)   
@receiver(post_save, sender=PaypalPayment, dispatch_uid="async_notify_user_payment_paypal_once")
def async_notify_user_payment_paypal(sender, instance, created, **kwargs):
    if created:
        pk = instance.pk
        transaction.on_commit(lambda: notify_user_payment_paypal.delay(pk))


# Payment signals (Stripe)
@receiver(post_save, sender=StripePayment, dispatch_uid="async_notify_user_payment_stripe_once")
def async_notify_user_payment_stripe(sender, instance, created, **kwargs):
    if created:
        pk = instance.pk
        transaction.on_commit(lambda: notify_user_payment_stripe.delay(pk))


# 드라이버 변경 시 driver_calendar_event_id 초기화
@receiver(pre_save, sender=Post, dispatch_uid="reset_driver_calendar_event_id_once")
def reset_driver_calendar_event_id(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Post.objects.get(pk=instance.pk)
        if old.driver != instance.driver:
            if (
                old.driver_calendar_event_id
                and old.driver
                and old.driver.google_calendar_id
            ):
                from utils.calendar_sync import delete_from_calendar
                delete_from_calendar(old.driver.google_calendar_id, old.driver_calendar_event_id)
            instance.driver_calendar_event_id = None
    except Post.DoesNotExist:
        pass


# google calendar recording 
@receiver(post_save, sender=Post, dispatch_uid="async_create_event_on_calendar_once")
def async_create_event_on_calendar(sender, instance, created, **kwargs):
    pk = instance.pk
    transaction.on_commit(lambda: create_event_on_calendar.delay(pk))
    

# check missing direction when flight number exists and missing flight contact info
@receiver(post_save, sender=Post, dispatch_uid="check_missing_info_once")
def check_missing_info(sender, instance, created, **kwargs):
    if created:
        pk = instance.pk
        if instance.flight_number and not (instance.direction and instance.direction.strip()):
            transaction.on_commit(lambda: send_missing_direction_email_task.delay(pk))
        transaction.on_commit(lambda: check_and_send_missing_info_email_task.delay(pk))


# sender를 문자열로 지정: "앱이름.모델이름"
@receiver(post_save, sender='articles.Post')
def update_sitemap_from_blog(sender, instance, created, **kwargs):
    if instance.status == 'published':
        from articles.models import Post
        call_command('generate_sitemap')