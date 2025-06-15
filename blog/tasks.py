import datetime
import os
import re
import logging

from googleapiclient.discovery import build
from google.oauth2 import service_account
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import Q
from celery import shared_task
from main.settings import RECIPIENT_EMAIL, DEFAULT_FROM_EMAIL
from .models import Post, PaypalPayment, StripePayment
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone


logger = logging.getLogger('easygo')


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@shared_task
def create_event_on_calendar(instance_id):    
    # Fetch the Post instance
    instance = Post.objects.get(pk=instance_id)

    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'secure/calendar/calendar-service-account-file.json'
    DELEGATED_USER_EMAIL = RECIPIENT_EMAIL  

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=DELEGATED_USER_EMAIL)

    service = build('calendar', 'v3', credentials=credentials)  

    reminder_str = '!' if instance.reminder else ''
    cancelled_str = 'C' if instance.cancelled else ''
    pending_str = '?' if instance.price == 'TBA' else ''
    pickup_time_str = instance.pickup_time or ''
    flight_number_str = instance.flight_number or ''
    start_point_str = instance.start_point or ''
    flight_time_str = instance.flight_time or ''
    no_of_passenger_str = f'p{instance.no_of_passenger}' if instance.no_of_passenger is not None else ''
    paid_str = 'paid' if instance.paid else ''    
    price_str = f'${instance.price}' if instance.price is not None else ''
    contact_str = instance.contact or ''
    suburb_str = instance.suburb or ''
    street_str = instance.street or ''    
    end_point_str = instance.end_point or ''

    title = " ".join([ 
        reminder_str, 
        cancelled_str,
        pending_str, 
        pickup_time_str, 
        flight_number_str,
        start_point_str, 
        flight_time_str, 
        no_of_passenger_str,
        paid_str, 
        price_str,
        contact_str        
    ]).strip()    

    if suburb_str and street_str:
        address = " ".join([street_str, suburb_str]).strip()
    elif street_str:
        address = " ".join([street_str, end_point_str]).strip()
    elif suburb_str:
        address = suburb_str
    else:
        address = end_point_str

    message_parts = [instance.name, instance.email, 
                     'b:'+str(instance.no_of_baggage) if instance.no_of_baggage is not None else '', 
                     'm:'+instance.message if instance.message is not None else '', 
                     'n:'+instance.notice if instance.notice is not None else '', 
                     "d:"+str(instance.return_pickup_date), 
                     '$'+str(instance.paid) if instance.paid is not None else '',
                     'opt:'+instance.end_point if instance.end_point is not None else '']
    message = " ".join(filter(None, message_parts))      

    pickup_date = datetime.datetime.strptime(str(instance.pickup_date), '%Y-%m-%d')

    if instance.pickup_time:
        pickup_time = datetime.datetime.strptime(instance.pickup_time, '%H:%M')

    else:
        pickup_time = datetime.datetime.strptime('00:00', '%H:%M') 

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

    # Check if an event already exists for this instance
    # if instance.cancelled:
    #     pass
    # else:
    if instance.calendar_event_id:
        pass
        event = service.events().update(calendarId='primary', eventId=instance.calendar_event_id, body=event).execute()
    else:
        event = service.events().insert(calendarId='primary', body=event).execute()
        instance.calendar_event_id = event['id']
        instance.save()


# Clicked confirm_booking form 
@shared_task
def send_confirm_email(name, email, pickup_date, return_flight_number):
    content = f'''
    {name}
    clicked the 'confirm booking' \n
    >> Sending email only! \n
    https://easygoshuttle.com.au/sending_email_first/ \n  
    https://easygoshuttle.com.au/sending_email_second/
    =============================   
    Email:  {email}
    Flight date: {pickup_date}
    Return flight number: {return_flight_number}
    ===============================          
    '''
    send_mail(pickup_date, content, DEFAULT_FROM_EMAIL, [RECIPIENT_EMAIL])


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


# PayPal payment record and email 
@shared_task
def notify_user_payment_paypal(instance_id):
    instance = PaypalPayment.objects.get(id=instance_id)

    if instance.name:
        posts = Post.objects.filter(
            (
                Q(name__iregex=r'^%s$' % re.escape(instance.name)) |
                Q(email__iexact=instance.email) |
                Q(email1__iexact=instance.email)
            ),
            pickup_date__gte=timezone.now().date()  # 오늘 이후
        ).order_by('pickup_date')  # 가장 가까운 순

        amount = round(float(instance.amount or 0) / 1.03, 2)
        recipient_emails = set()

        if posts.exists():
            remaining_amount = amount
            total_price = 0.0
            total_paid_before = 0.0
            total_paid_after = 0.0

            for post in posts:
                price = float(post.price or 0)
                paid = float(post.paid or 0)
                balance = round(price - paid, 2)

                total_price += price
                total_paid_before += paid

                if balance <= 0:
                    continue

                if remaining_amount >= balance:
                    post.paid = str(price)
                    remaining_amount -= balance
                else:
                    post.paid = str(paid + remaining_amount)
                    remaining_amount = 0

                try:
                    total_paid_after += float(post.paid or 0)
                except (ValueError, TypeError):
                    total_paid_after += 0.0

                post.toll = "" if float(post.paid) >= price else "short payment"
                post.cash = False
                post.reminder = True
                post.discount = ""
                post.save()

                recipient_emails.update([post.email, post.email1])

                if remaining_amount <= 0:
                    break

            # 이메일 한 번만 발송
            recipient_list = [email for email in recipient_emails if email] + [RECIPIENT_EMAIL]

            if total_paid_after >= total_price:
                html_content = render_to_string(
                    "basecamp/html_email-payment-success.html",
                    {'name': instance.name, 'email': instance.email, 'amount': amount}
                )
            else:
                html_content = render_to_string(
                    "basecamp/html_email-response-discrepancy.html",
                    {
                        'name': instance.name,
                        'price': round(total_price, 2),
                        'paid': round(total_paid_before + amount, 2),
                        'diff': round(total_price - (total_paid_before + amount), 2)
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
                Q(name__iregex=r'^%s$' % re.escape(instance.name)) |
                Q(email__iexact=instance.email) |
                Q(email1__iexact=instance.email)
            ),
            pickup_date__gte=timezone.now().date()  # 오늘 이후
        ).order_by('pickup_date')  # 가장 가까운 순   

        amount = round(float(instance.amount or 0), 2)
        recipient_emails = set()

        if posts.exists():
            remaining_amount = amount
            total_price = 0.0
            total_paid_before = 0.0
            total_paid_after = 0.0

            for post in posts:
                price = float(post.price or 0)
                paid = float(post.paid or 0)
                balance = round(price - paid, 2)

                total_price += price
                total_paid_before += paid

                if balance <= 0:
                    continue  # 이미 결제된 예약은 건너뜀

                if remaining_amount >= balance:
                    post.paid = price
                    remaining_amount -= balance
                else:
                    post.paid = paid + remaining_amount
                    remaining_amount = 0.0

                total_paid_after += float(post.paid or 0)

                post.toll = "" if post.paid >= price else "short payment"
                post.cash = ""
                post.reminder = True
                post.discount = ""
                post.save()

                recipient_emails.update([post.email, post.email1])

                if remaining_amount <= 0:
                    break

            # 이메일 한 번만 발송
            recipient_list = [email for email in recipient_emails if email] + [RECIPIENT_EMAIL]

            if total_paid_after >= total_price:
                html_content = render_to_string(
                    "basecamp/html_email-payment-success-stripe.html",
                    {'name': instance.name, 'email': instance.email, 'amount': amount}
                )
            else:
                html_content = render_to_string(
                    "basecamp/html_email-response-discrepancy.html",
                    {
                        'name': instance.name,
                        'price': round(total_price, 2),
                        'paid': round(total_paid_before + amount, 2),
                        'diff': round(total_price - (total_paid_before + amount), 2)
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

            