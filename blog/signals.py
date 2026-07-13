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
    logger.info('notify_user_inquiry: Inquiry pk=%s created=%s sent_email=%s', instance.pk, created, instance.sent_email)
    if not instance.sent_email:
        pk = instance.pk
        transaction.on_commit(lambda: send_inquiry_email_task.delay(pk))
        logger.info('notify_user_inquiry: queued send_inquiry_email_task for Inquiry pk=%s', pk)


# Post signals
@receiver(post_save, sender=Post, dispatch_uid="notify_user_post_once")
def notify_user_post(sender, instance, created, **kwargs):
    update_fields = kwargs.get('update_fields')

    try:
        handle_return_trip(instance)
    except Exception:
        logger.error('notify_user_post: handle_return_trip failed for Post pk=%s', instance.pk, exc_info=True)

    update_data = {}

    try:
        if instance.price in [None, "", "TBA"] or float(instance.price) == 0.0:
            update_data['price'] = "TBA"
    except (ValueError, TypeError):
        pass

    if not instance.cash and not instance.paid:
        update_data['pending'] = True

    if instance.is_confirmed:
        pk = instance.pk
        transaction.on_commit(lambda: send_post_confirmation_email_task.delay(pk))

    if update_data:
        Post.objects.filter(pk=instance.pk).update(**update_data)


# Send email notification if a Post is cancelled and email hasn't been sent yet
@receiver(post_save, sender=Post, dispatch_uid="notify_user_post_cancelled_once")
def notify_user_post_cancelled(sender, instance, created, **kwargs):
    update_fields = kwargs.get('update_fields')

    if update_fields and 'cancelled' in update_fields:
        logger.info('notify_user_post_cancelled: skipping Post pk=%s (update_fields contains cancelled)', instance.pk)
        return

    if instance.sent_email:
        logger.info('notify_user_post_cancelled: skipping Post pk=%s (sent_email=True)', instance.pk)
        return

    if instance.cancelled:
        pk = instance.pk
        transaction.on_commit(lambda: send_post_cancelled_email_task.delay(pk))
        logger.info('notify_user_post_cancelled: queued send_post_cancelled_email_task for Post pk=%s', pk)


# Automatically set prepay to True for foreign contacts or company names
@receiver(post_save, sender=Post, dispatch_uid="set_prepay_for_foreign_users")
def set_prepay_for_foreign_users(sender, instance, created, **kwargs):
    if not instance.pk or instance.cash:
        return

    if not instance.prepay:
        if is_foreign_number(instance.contact) or (instance.company_name or "").strip():
            Post.objects.filter(pk=instance.pk).update(prepay=True)
            logger.info('set_prepay_for_foreign_users: set prepay=True for Post pk=%s', instance.pk)


# Payment signals (Paypal)
@receiver(post_save, sender=PaypalPayment, dispatch_uid="async_notify_user_payment_paypal_once")
def async_notify_user_payment_paypal(sender, instance, created, **kwargs):
    logger.info('async_notify_user_payment_paypal: PaypalPayment pk=%s created=%s', instance.pk, created)
    if created:
        pk = instance.pk
        transaction.on_commit(lambda: notify_user_payment_paypal.delay(pk))
        logger.info('async_notify_user_payment_paypal: queued notify_user_payment_paypal for pk=%s', pk)


# Payment signals (Stripe)
@receiver(post_save, sender=StripePayment, dispatch_uid="async_notify_user_payment_stripe_once")
def async_notify_user_payment_stripe(sender, instance, created, **kwargs):
    logger.info('async_notify_user_payment_stripe: StripePayment pk=%s created=%s', instance.pk, created)
    if created:
        pk = instance.pk
        transaction.on_commit(lambda: notify_user_payment_stripe.delay(pk))
        logger.info('async_notify_user_payment_stripe: queued notify_user_payment_stripe for pk=%s', pk)


# 드라이버 변경 시 driver_calendar_event_id 초기화 + proxy 비교용 이전 값 보존
@receiver(pre_save, sender=Post, dispatch_uid="reset_driver_calendar_event_id_once")
def reset_driver_calendar_event_id(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Post.objects.get(pk=instance.pk)
        instance._pre_save_driver_id = old.driver_id
        instance._pre_save_use_proxy = old.use_proxy
        if old.driver != instance.driver:
            logger.info(
                'reset_driver_calendar_event_id: driver changed for Post pk=%s old_driver=%s new_driver=%s',
                instance.pk, old.driver_id, instance.driver_id,
            )
            if (
                old.driver_calendar_event_id
                and old.driver
                and old.driver.google_calendar_id
            ):
                try:
                    from utils.calendar_sync import delete_from_calendar
                    delete_from_calendar(old.driver.google_calendar_id, old.driver_calendar_event_id)
                except Exception:
                    logger.error(
                        'reset_driver_calendar_event_id: delete_from_calendar failed for Post pk=%s event_id=%s',
                        instance.pk, old.driver_calendar_event_id, exc_info=True,
                    )
            instance.driver_calendar_event_id = None
            logger.info('reset_driver_calendar_event_id: cleared driver_calendar_event_id for Post pk=%s', instance.pk)
    except Post.DoesNotExist:
        pass


# google calendar recording
CALENDAR_EXCLUDED_FIELDS = {
    'company_name', 'booker_name', 'booker_email', 'booker_contact', 'email1',
    'return_direction', 'return_flight_number', 'return_flight_time',
    'return_pickup_time', 'return_start_point', 'return_end_point',
    'discount', 'surcharge', 'region', 'is_confirmed',
    'cruise', 'sms_reminder', 'prepay',
    'calendar_event_id', 'driver_calendar_event_id', 'use_proxy', 'created',
}

@receiver(post_save, sender=Post, dispatch_uid="async_create_event_on_calendar_once")
def async_create_event_on_calendar(sender, instance, created, update_fields, **kwargs):
    logger.info(
        'async_create_event_on_calendar: Post pk=%s created=%s update_fields=%s calendar_event_id=%r',
        instance.pk, created, list(update_fields) if update_fields else None, instance.calendar_event_id,
    )
    if update_fields is not None and set(update_fields).issubset(CALENDAR_EXCLUDED_FIELDS):
        logger.info(
            'async_create_event_on_calendar: skipping Post pk=%s — update_fields %s are all excluded',
            instance.pk, list(update_fields),
        )
        return
    pk = instance.pk
    transaction.on_commit(lambda: create_event_on_calendar.delay(pk))
    logger.info('async_create_event_on_calendar: queued create_event_on_calendar for Post pk=%s', pk)


# check missing direction when flight number exists and missing flight contact info
@receiver(post_save, sender=Post, dispatch_uid="check_missing_info_once")
def check_missing_info(sender, instance, created, **kwargs):
    if created:
        pk = instance.pk
        if instance.flight_number and not (instance.direction and instance.direction.strip()):
            transaction.on_commit(lambda: send_missing_direction_email_task.delay(pk))
            logger.info('check_missing_info: queued send_missing_direction_email_task for Post pk=%s', pk)
        transaction.on_commit(lambda: check_and_send_missing_info_email_task.delay(pk))
        logger.info('check_missing_info: queued check_and_send_missing_info_email_task for Post pk=%s', pk)


# driver가 None이거나 use_proxy가 False이면 매핑 해제,
# driver가 있고 use_proxy가 True이면 매핑 재생성
@receiver(post_save, sender=Post, dispatch_uid="close_bird_mapping_on_no_driver_once")
def close_bird_mapping_on_no_driver(sender, instance, created, **kwargs):
    from blog.bird_proxy import close_bird_mapping, create_bird_mapping

    if created:
        if instance.use_proxy and instance.driver:
            if is_foreign_number(instance.contact):
                logger.info('close_bird_mapping_on_no_driver: skipping Bird mapping for foreign contact Post pk=%s', instance.pk)
            else:
                try:
                    create_bird_mapping(instance)
                    logger.info('close_bird_mapping_on_no_driver: created bird mapping for new Post pk=%s', instance.pk)
                except Exception:
                    logger.error('close_bird_mapping_on_no_driver: create_bird_mapping failed for Post pk=%s', instance.pk, exc_info=True)
        return

    update_fields = kwargs.get('update_fields')
    if update_fields is not None:
        proxy_fields = {'use_proxy', 'driver', 'driver_id'}
        if not proxy_fields.intersection(update_fields):
            return
    elif hasattr(instance, '_pre_save_use_proxy'):
        driver_changed = instance._pre_save_driver_id != instance.driver_id
        use_proxy_changed = instance._pre_save_use_proxy != instance.use_proxy
        if not driver_changed and not use_proxy_changed:
            return

    if instance.driver is None or not instance.use_proxy:
        ok = close_bird_mapping(instance)
        if ok:
            logger.info('close_bird_mapping_on_no_driver: Bird mapping closed for Post %s (driver=%s, use_proxy=%s)',
                        instance.pk, instance.driver, instance.use_proxy)
        else:
            logger.warning('close_bird_mapping_on_no_driver: Bird mapping close failed for Post %s', instance.pk)
    else:
        if is_foreign_number(instance.contact):
            logger.info('close_bird_mapping_on_no_driver: skipping Bird mapping for foreign contact Post %s', instance.pk)
        else:
            ok = create_bird_mapping(instance)
            if ok:
                logger.info('close_bird_mapping_on_no_driver: Bird mapping created for Post %s', instance.pk)
            else:
                logger.warning('close_bird_mapping_on_no_driver: Bird mapping create failed for Post %s', instance.pk)


# sender를 문자열로 지정: "앱이름.모델이름"
@receiver(post_save, sender='articles.Post', dispatch_uid="update_sitemap_from_blog_once")
def update_sitemap_from_blog(sender, instance, created, **kwargs):
    if instance.status == 'published':
        from articles.models import Post
        call_command('generate_sitemap')