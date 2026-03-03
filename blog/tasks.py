import os
import logging

from django.core.mail import send_mail, EmailMultiAlternatives
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal

from celery import shared_task
from main.settings import RECIPIENT_EMAIL, DEFAULT_FROM_EMAIL
from .models import Post, PaypalPayment, StripePayment
from .blog_utils import process_generic_payment, send_payment_notification_email
from utils.calendar_sync import sync_to_calendar
from basecamp.basecamp_utils import render_email_template


logger = logging.getLogger('easygo')


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Google Calendar event 
@shared_task
def create_event_on_calendar(instance_id):    
    try:
        instance = Post.objects.get(pk=instance_id)
    except Post.DoesNotExist:
        logger.warning(f"Post with id {instance_id} does not exist.")
        return 

    event_id = (instance.calendar_event_id or '').strip()

    # 취소 상태면서 기존 이벤트 없으면 새로 생성 안 함
    if instance.cancelled and not event_id:
        logger.info(f"Cancelled post {instance_id} with no event_id. Skipping event creation.")
        return

    # Google Calendar 동기화
    sync_to_calendar(instance)


# Clicked confirm_booking form 
@shared_task
def send_confirm_email(
    name, email, contact, company_name, direction, flight_number, flight_time,
    pickup_date, pickup_time, return_flight_number, street, suburb, start_point, 
    end_point, cash, prepay, return_start_point, return_end_point):
    subject = f"Booking Confirmation Clicked"
    
    content = f'''
    {name} clicked the 'confirm booking' 

    ✅ Sending email only! 

    👉 https://easygoshuttle.com.au/sending_email_first/
    
    
    👉 https://easygoshuttle.com.au/sending_email_second/

    =============================   
    Email:  {email}
    Contact: {contact}
    Company name: {company_name}
    Direction: {direction}
    Flight number: {flight_number}
    Flight time: {flight_time}
    Flight date: {pickup_date}
    Pickup time: {pickup_time}
    ✅ *** Return flight number: {return_flight_number} ***
    ✅ *** Return Pickup Location: {return_start_point} ***
    ✅ *** Return Drop-off Location {return_end_point} ***
    Street: {street}
    Suburb: {suburb}
    Start point: {start_point}
    End point: {end_point}
    Cash: {cash}
    Prepay: {prepay}    
    ===============================          
    '''

    send_mail(subject, content, DEFAULT_FROM_EMAIL, [RECIPIENT_EMAIL])


# Home page for price 
@shared_task
def send_email_task(pickup_date, direction, suburb, no_of_passenger):
    content = f'''
    someone checked the price from homepage    
    =============================  
    flight date:  {pickup_date}
    Direction: {direction}
    Suburbs: {suburb}
    No of Pax: {no_of_passenger}
    ===============================        
    '''
    send_mail(pickup_date, content, DEFAULT_FROM_EMAIL, [RECIPIENT_EMAIL])


# Review page, service, information, terms, policy
@shared_task
def send_notice_email(subject, message, RECIPIENT_EMAIL):
    if not all([subject, message, RECIPIENT_EMAIL]):
        raise ValueError("Subject, message, and recipient email must be provided")
            
    if not DEFAULT_FROM_EMAIL:
        raise ImproperlyConfigured("DEFAULT_FROM_EMAIL is not set in environment variables")
    
    send_mail(
        subject,
        message,
        DEFAULT_FROM_EMAIL,
        [RECIPIENT_EMAIL],
        fail_silently=False,
    )


# PayPal payment 
@shared_task
def notify_user_payment_paypal(instance_id):
    with transaction.atomic():
        try:
            instance = PaypalPayment.objects.select_for_update().get(id=instance_id)
        except PaypalPayment.DoesNotExist:
            return
        
        raw_amount = float(instance.amount or 0)
        calculated_amount = round(raw_amount / 1.03, 2)
        
        # 원본 금액 보존 (이메일 발송용)
        original_amount = instance.amount
        # 배분 로직용 금액 설정
        instance.amount = calculated_amount 

        posts = Post.objects.filter(
            Q(email__iexact=instance.email) | 
            Q(name__iexact=instance.name)
        ).order_by('pickup_date')
        
        success, total_balance, recipient_emails = process_generic_payment(
            instance, posts, RECIPIENT_EMAIL
        )
        
        # 배분 후 다시 원금으로 복구 (이메일 템플릿의 raw_amount 표시를 위해)
        instance.amount = original_amount
        
        if not success: return

    send_payment_notification_email(instance, total_balance, recipient_emails, RECIPIENT_EMAIL)


# Stripe payment 
@shared_task
def notify_user_payment_stripe(instance_id):
    with transaction.atomic():
        try:
            instance = StripePayment.objects.select_for_update().get(id=instance_id)
        except StripePayment.DoesNotExist:
            return

        posts = Post.objects.filter(
            Q(email__iexact=instance.email) | 
            Q(name__iexact=instance.name)
        ).order_by('pickup_date')

        # 2. 금액 배분 로직 실행
        success, total_balance, recipient_emails = process_generic_payment(
            instance, posts, RECIPIENT_EMAIL
        )
        
        if not success: return # 중복 건이면 종료

    # 3. 이메일 발송 (트랜잭션 밖에서 실행)
    send_payment_notification_email(instance, total_balance, recipient_emails, RECIPIENT_EMAIL)

            
# XRP payment record and email
@shared_task
def send_xrp_internal_email(subject, message, from_email, recipient_list):
    """회사 내부 알림(텍스트)"""
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=False,
    )

@shared_task
def send_xrp_customer_email(email: str, xrp_amount: str, xrp_address: str, dest_tag: int):
    """
    고객에게 XRP 결제 안내 메일 전송 (HTML, 이름 없음)
    QR 코드 기능 제거 버전
    """

    # context를 단일 dict로 구성 (QR코드 제거)
    context = {
        "email": email,
        "amount": f"{Decimal(xrp_amount):.2f} XRP",
        "address": xrp_address,
        "dest_tag": dest_tag,
    }

    # HTML 렌더링
    html_content = render_email_template("html_email-xrppayment.html", context)

    # 이메일 생성
    subject = "XRP Payment - EasyGo"
    mail = EmailMultiAlternatives(
        subject,
        html_content,
        RECIPIENT_EMAIL,  # 발신자
        [email],          # 수신자
    )
    mail.attach_alternative(html_content, "text/html")

    # 이메일 전송
    try:
        mail.send()
    except Exception as e:
        logger.exception("Failed to send XRP payment email: %s", e)


