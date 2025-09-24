import datetime
import os
import re
import logging, qrcode, base64

from decimal import Decimal, InvalidOperation

from googleapiclient.discovery import build
from google.oauth2 import service_account
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import Q
from celery import shared_task
from main.settings import RECIPIENT_EMAIL, DEFAULT_FROM_EMAIL
from .models import Post, PaypalPayment, StripePayment, XrpPayment
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from io import BytesIO


logger = logging.getLogger('easygo')


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'secure/calendar/calendar-service-account-file.json'
    DELEGATED_USER_EMAIL = RECIPIENT_EMAIL  

    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=DELEGATED_USER_EMAIL
        )
        service = build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        logger.error(f"Failed to build Google Calendar service: {e}")
        return
  
    # 구글해드(title)에 들어갈 것들 
    reminder_str = '!' if instance.reminder else ''
    cancelled_str = 'C' if instance.cancelled else ''
    pending_str = '?' if instance.price == 'TBA' else ''
    pickup_time_str = instance.pickup_time or ''
    flight_number_str = instance.flight_number or ''
    start_point_str = instance.start_point or ''
    flight_time_str = instance.flight_time or ''
    no_of_passenger_str = f'p{instance.no_of_passenger}' if instance.no_of_passenger is not None else ''
    paid_str = 'paid' if instance.paid else ''  
    cash_str = 'cash' if instance.cash else ''  
    price_str = f'${instance.price}' if instance.price is not None else ''
    contact_str = instance.contact or ''
    suburb_str = instance.suburb or ''
    street_str = instance.street or ''    
    end_point_str = instance.end_point or ''

    title = " ".join(filter(None, [ 
        reminder_str, 
        cancelled_str,
        pending_str, 
        pickup_time_str, 
        flight_number_str,
        start_point_str, 
        flight_time_str, 
        no_of_passenger_str,
        paid_str, 
        cash_str,  
        price_str,
        contact_str        
    ])).strip()    

    # address 구성
    if suburb_str and street_str:
        address = " ".join([street_str, suburb_str]).strip()
    elif street_str:
        address = " ".join([street_str, end_point_str]).strip()
    elif suburb_str:
        address = suburb_str
    else:
        address = end_point_str

    # description (message) 구성
    message_parts = [instance.name, instance.email, 
                     'b:'+str(instance.no_of_baggage) if instance.no_of_baggage is not None else '', 
                     'm:'+instance.message if instance.message is not None else '', 
                     'n:'+instance.notice if instance.notice is not None else '', 
                     "d:"+str(instance.return_pickup_date) if instance.return_pickup_date is not None else '', 
                     '$'+str(instance.paid) if instance.paid is not None else '',
                     'private' if instance.private_ride is not None else '', 
                     'opt:'+instance.end_point if instance.end_point is not None else '']
    message = " ".join(filter(None, message_parts))      

    # 날짜와 시간 파싱
    try:
        pickup_date = datetime.datetime.strptime(str(instance.pickup_date), '%Y-%m-%d')
    except Exception as e:
        logger.error(f"Invalid date for post {instance_id}: {e}")
        return 

    try:
        pickup_time = datetime.datetime.strptime(instance.pickup_time or '00:00', '%H:%M')
    except Exception as e:
        logger.error(f"Invalid time for post {instance_id}: {e}")
        return

    start = datetime.datetime.combine(pickup_date, pickup_time.time())        
    end = start + datetime.timedelta(hours=1)

    event = {
        'summary': title,
        'location': address,
        'start': {
            'dateTime': start.strftime('%Y-%m-%dT%H:%M:%S'),
            'timeZone': 'Australia/Sydney',
        },
        'end': {
            'dateTime': end.strftime('%Y-%m-%dT%H:%M:%S'),
            'timeZone': 'Australia/Sydney',
        },
        'description': message,
    }    

    # 구글 캘린더 이벤트 처리
    try:
        if event_id:
            service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        else:
            new_event = service.events().insert(calendarId='primary', body=event).execute()
            instance.calendar_event_id = new_event['id']
            instance.save(update_fields=['calendar_event_id'])
    except Exception as e:
        logger.error(f"Failed to sync Google Calendar event for post {instance_id}: {e}")
        return


# Clicked confirm_booking form 
@shared_task
def send_confirm_email(
    name, email, contact, company_name, direction, flight_number, flight_time,
    pickup_date, pickup_time, return_flight_number, street, suburb, start_point, 
    end_point, cash, prepay):
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
    

def payment_send_email(subject, html_content, recipient_list):
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        subject,
        text_content,
        DEFAULT_FROM_EMAIL,
        recipient_list
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


def clean_float(value):
    try:
        return "{:.2f}".format(float(value)).rstrip('0').rstrip('.')
    except (ValueError, TypeError):
        return "0"


# PayPal payment record and email 
@shared_task
def notify_user_payment_paypal(instance_id):
    instance = PaypalPayment.objects.get(id=instance_id)

    if instance.name:
        posts = Post.objects.filter(
            (
                Q(name__iexact=instance.name.strip()) |
                Q(email__iexact=instance.email.strip()) |
                Q(email1__iexact=instance.email.strip())
            ),
            pickup_date__gte=timezone.now().date()
        ).order_by('pickup_date')

        try:
            raw_amount = float(instance.amount or 0)
            amount = round(raw_amount / 1.03, 2)
        except (ValueError, TypeError):
            return
         
        recipient_emails = set()

        if posts.exists():
            # 전체 미납액 계산 
            total_balance = 0.0
            for post in posts:
                try:
                    price = float(post.price or 0)
                except (ValueError, TypeError):
                    price = 0.0

                try:
                    paid = float(post.paid)
                except (ValueError, TypeError):
                    paid = 0.0
                balance = round(price - paid, 2)

                if balance > 0:
                    total_balance += balance

            remaining_amount = amount

            for post in posts:
                try:
                    price = float(post.price or 0)
                except (ValueError, TypeError):
                    price = 0.0

                try:
                    paid = float(post.paid or 0)
                except (ValueError, TypeError):
                    paid = 0.0

                balance = round(price - paid, 2)

                if balance <= 0:
                    continue  # 이미 전액 결제된 예약 건너뜀

                if remaining_amount >= balance:
                    paid_new = price
                    remaining_amount -= balance
                else:
                    paid_new = paid + remaining_amount
                    remaining_amount = 0.0

                post.paid = clean_float(paid_new)
                post.toll = "" if paid_new >= price else "short payment"
                post.cash = False
                post.reminder = True
                post.discount = ""

                original_notice = post.notice or ""
                notice_parts = [original_notice.strip()]
                new_notice_entry = f"===PAYPAL=== paid: ${amount:.2f}"

                if new_notice_entry not in original_notice:
                    notice_parts.append(new_notice_entry)
                    post.notice = " | ".join(filter(None, notice_parts)).strip()

                post.save()

                recipient_emails.update([post.email, post.email1])

                if remaining_amount <= 0:
                    break

            remaining_balance_after_payment = total_balance - amount

            # Check if no money was applied (means: all bookings were already paid)
            if remaining_amount == amount:
                # Notify admin (you)
                admin_notice = f'''
            ⚠️ PayPal Overpayment Detected

            Name: {instance.name}
            Email: {instance.email}
            Paid: ${amount:.2f}

            No bookings were updated because all are already paid in full.
            Please check if refund or future booking credit is needed.
                '''
                send_mail(
                    subject="⚠️ PayPal Overpayment Alert - EasyGo",
                    message=admin_notice,
                    from_email=DEFAULT_FROM_EMAIL,
                    recipient_list=[RECIPIENT_EMAIL],  # only to you
                )

            recipient_list = [email for email in recipient_emails if email] + [RECIPIENT_EMAIL]

            if remaining_balance_after_payment <= 0:
                html_content = render_to_string(
                    "basecamp/html_email-payment-success.html",
                    {
                        'name': instance.name,
                        'email': instance.email,
                        'amount': amount,
                        'raw_amount': raw_amount
                    }
                )
            else:
                html_content = render_to_string(
                    "basecamp/html_email-response-discrepancy.html",
                    {
                        'name': instance.name,
                        'price': round(total_balance, 2),
                        'paid': round(amount, 2),
                        'diff': round(remaining_balance_after_payment, 2)
                    }
                )

            payment_send_email("Payment - EasyGo", html_content, recipient_list)

        else:
            html_content = render_to_string(
                "basecamp/html_email-noIdentity.html",
                {'name': instance.name, 'email': instance.email, 'amount': amount}
            )
            recipient_list = [email for email in [instance.email, RECIPIENT_EMAIL] if email]
            payment_send_email("Payment - EasyGo", html_content, recipient_list)


# Stripe > sending email & save
@shared_task
def notify_user_payment_stripe(instance_id):
    instance = StripePayment.objects.get(id=instance_id)

    if instance.name:
        posts = Post.objects.filter(
            (
                Q(name__iexact=instance.name.strip()) |
                Q(email__iexact=instance.email.strip()) |
                Q(email1__iexact=instance.email.strip())
            ),
            pickup_date__gte=timezone.now().date()  
        ).order_by('pickup_date')   

        try:
            raw_amount = float(instance.amount or 0)
            amount = round(raw_amount, 2)
        except (ValueError, TypeError):
            return
        
        recipient_emails = set()

        if posts.exists():
            # 전체 미납액 계산
            total_balance = 0.0
            for post in posts:
                try:
                    price = float(post.price or 0)
                except (ValueError, TypeError):
                    price = 0.0

                try:
                    paid = float(post.paid or 0)
                except (ValueError, TypeError):
                    paid = 0.0

                balance = round(price - paid, 2)

                if balance > 0:
                    total_balance += balance

            remaining_amount = amount

            for post in posts:
                try:
                    price = float(post.price or 0)
                except (ValueError, TypeError):
                    price = 0.0

                try:
                    paid = float(post.paid)
                except (ValueError, TypeError):
                    paid = 0.0

                balance = round(price - paid, 2)

                if balance <= 0:
                    continue  # 이미 결제된 예약은 건너뜀

                if remaining_amount >= balance:
                    paid_new = price
                    remaining_amount -= balance
                else:
                    paid_new = paid + remaining_amount
                    remaining_amount = 0.0

                post.paid = clean_float(paid_new)
                post.toll = "" if paid_new >= price else "short payment"
                post.cash = False
                post.reminder = True
                post.discount = ""

                original_notice = post.notice or ""
                notice_parts = [original_notice.strip()]
                new_notice_entry = f"===STRIPE=== paid: ${amount:.2f}"

                # 중복 방지 조건 추가
                if new_notice_entry not in original_notice:
                    notice_parts.append(new_notice_entry)
                    post.notice = " | ".join(filter(None, notice_parts)).strip()

                post.save()

                recipient_emails.update([post.email, post.email1])

                if remaining_amount <= 0:
                    break

            remaining_balance_after_payment = total_balance - amount

            # Check if no money was applied (means: all bookings were already paid)
            if remaining_amount == amount:
                # Notify admin (you)
                admin_notice = f'''
            ⚠️ Stripe Overpayment Detected

            Name: {instance.name}
            Email: {instance.email}
            Paid: ${amount:.2f}

            No bookings were updated because all are already paid in full.
            Please check if refund or future booking credit is needed.
                '''
                send_mail(
                    subject="⚠️ Stripe Overpayment Alert - EasyGo",
                    message=admin_notice,
                    from_email=DEFAULT_FROM_EMAIL,
                    recipient_list=[RECIPIENT_EMAIL],  # only to you
                )

            # 이메일 한 번만 발송
            recipient_list = [email for email in recipient_emails if email] + [RECIPIENT_EMAIL]

            if remaining_balance_after_payment <= 0:
                html_content = render_to_string(
                    "basecamp/html_email-payment-success-stripe.html",
                    {'name': instance.name, 'email': instance.email, 'amount': amount}
                )
            else:
                html_content = render_to_string(
                    "basecamp/html_email-response-discrepancy.html",
                    {
                        'name': instance.name,
                        'price': round(total_balance, 2),
                        'paid': round(amount, 2),
                        'diff': round(remaining_balance_after_payment, 2)
                    }
                )

            payment_send_email("Payment - EasyGo", html_content, recipient_list)

        else:
            # 예약 찾지 못한 경우
            html_content = render_to_string(
                "basecamp/html_email-noIdentity-stripe.html",
                {'name': instance.name, 'email': instance.email, 'amount': amount}
            )
            recipient_list = [email for email in [instance.email, RECIPIENT_EMAIL] if email]
            payment_send_email("Payment - EasyGo", html_content, recipient_list)

            
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
    html_content = render_to_string("basecamp/html_email-xrppayment.html", context)

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
