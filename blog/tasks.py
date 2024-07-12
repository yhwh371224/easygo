import datetime
import os
import re

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

    cancelled_str = 'c' if instance.cancelled else ''
    reminder_str = '!' if instance.reminder else ''
    pending_str = '?' if instance.discount == 'TBA' else ''
    pickup_time_str = instance.pickup_time or ''
    flight_number_str = instance.flight_number or ''
    flight_time_str = instance.flight_time or ''
    no_of_passenger_str = f'p{instance.no_of_passenger}' if instance.no_of_passenger is not None else ''
    paid_str = 'paid' if instance.paid else ''    
    price_str = f'${instance.price}' if instance.price is not None else ''
    contact_str = instance.contact or ''
    suburb_str = instance.suburb if instance.suburb else 'NSW'

    title = " ".join([
        cancelled_str, 
        reminder_str, 
        pending_str, 
        pickup_time_str, 
        flight_number_str, 
        flight_time_str, 
        no_of_passenger_str,
        paid_str, 
        price_str,
        contact_str
    ]).strip()    

    address = " ".join([instance.street, suburb_str])        
    message_parts = [instance.name, instance.email, 
                     'b:'+str(instance.no_of_baggage) if instance.no_of_baggage is not None else '', 
                     'm:'+instance.message if instance.message is not None else '', 
                     'n:'+instance.notice if instance.notice is not None else '', 
                     "d:"+str(instance.return_pickup_date), 
                     '$'+str(instance.paid) if instance.paid is not None else '',
                     '!!'+instance.toll if instance.toll is not None else '']
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
    if instance.cancelled:
        pass
    else:
        if instance.calendar_event_id:
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
    if instance.item_name:
        post_name = Post.objects.filter(
            Q(name__iregex=r'^%s$' % re.escape(instance.name)) |
            Q(email__iexact=instance.email)
        ).first()

        if post_name:       
            html_content = render_to_string(
                "basecamp/html_email-payment-success.html",
                {'name': post_name.name, 'email': post_name.email, 'amount': instance.amount}
            )
            payment_send_email("Payment - EasyGo", html_content, [post_name.email, RECIPIENT_EMAIL])

            checking_message = "short payment"
            post_name.paid = instance.amount            
            post_name.reminder = True
            post_name.discount = ""
            if float(post_name.price) > float(instance.amount):
                post_name.toll = checking_message             
            post_name.save()

            if post_name.return_pickup_time == 'x':                   
                    second_post = Post.objects.filter(email=post_name.email)[1]                    
                    second_post.paid = instance.amount                    
                    second_post.reminder = True
                    second_post.discount = ""   
                    if float(second_post.price) > float(instance.amount):
                        post_name.toll = checking_message                    
                    second_post.save() 

        else:
            html_content = render_to_string(
                "basecamp/html_email-noIdentity.html",
                {'name': instance.name, 'email': instance.email, 'amount': instance.amount}
            )
            payment_send_email("Payment - EasyGo", html_content, [instance.email, RECIPIENT_EMAIL])


# Stripe > sending email & save
@shared_task
def notify_user_payment_stripe(instance_id):
    instance = StripePayment.objects.get(id=instance_id)   
    if instance.name:            
        post_name = Post.objects.filter(
            Q(name__iregex=r'^%s$' % re.escape(instance.name)) |
            Q(email__iexact=instance.email)
        ).first()

        if post_name:            
            html_content = render_to_string(
                "basecamp/html_email-payment-success-stripe.html",
                {'name': post_name.name, 'email': post_name.email, 'amount': instance.amount}
            )
            payment_send_email("Payment - EasyGo", html_content, [post_name.email, RECIPIENT_EMAIL])            
            
            post_name.paid = instance.amount          
            post_name.reminder = True
            post_name.discount = ""
            if float(post_name.price) > instance.amount:
                post_name.toll = "short payment"             
            post_name.save()

            if post_name.return_pickup_time == 'x':                   
                    second_post = Post.objects.filter(email=post_name.email)[1]                    
                    second_post.paid = instance.amount                    
                    second_post.reminder = True
                    second_post.discount = ""
                    if float(post_name.price) > instance.amount:
                        second_post.toll = "short payment"  
                    second_post.save() 

        else:            
            html_content = render_to_string(
                "basecamp/html_email-noIdentity-stripe.html",
                {'name': instance.name, 'email': instance.email, 'amount': instance.amount}
            )
            payment_send_email("Payment - EasyGo", html_content, [instance.email, RECIPIENT_EMAIL])


