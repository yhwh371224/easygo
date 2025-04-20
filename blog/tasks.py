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
        post_name = Post.objects.filter(
            Q(name__iregex=r'^%s$' % re.escape(instance.name)) |
            Q(email__iexact=instance.email)
        ).first()
        
        amount_value = instance.amount
        amount = round(float(amount_value) / 1.03, 2)
            
        if post_name:
            already_paid = float(post_name.paid or 0)
            total_paid = already_paid + amount
            price = float(post_name.price)

            if round(total_paid, 2) >= round(price, 2):
                html_content = render_to_string(
                    "basecamp/html_email-payment-success.html",
                    {'name': post_name.name, 'email': post_name.email, 'amount': amount}
                )
                payment_send_email("Payment - EasyGo", html_content, [post_name.email, RECIPIENT_EMAIL])
                post_name.toll = ""

            else:
                post_name.toll = "short payment"
                diff = round(price - total_paid, 2)
                html_content = render_to_string(
                    "basecamp/html_email-response-discrepancy.html",
                    {'name': post_name.name, 'price': price, 'paid': total_paid, 'diff': diff}
                )
                payment_send_email("Payment - EasyGo", html_content, [post_name.email, RECIPIENT_EMAIL])
            
            post_name.paid = total_paid
            post_name.reminder = True
            post_name.discount = ""
            post_name.save()

            if post_name.return_pickup_time == 'x':
                second_post = Post.objects.filter(email=post_name.email)[1]                    
                already_paid_second = float(second_post.paid or 0)
                total_paid_second = already_paid_second + amount
                price_second = float(second_post.price)

                if round(total_paid_second, 2) >= round(price, 2):
                    html_content = render_to_string(
                        "basecamp/html_email-payment-success.html",
                        {'name': second_post.name, 'email': second_post.email, 'amount': amount}
                    )
                    payment_send_email("Payment - EasyGo", html_content, [second_post.email, RECIPIENT_EMAIL])
                    second_post.toll = ""

                else:
                    second_post.toll = "short payment"
                    diff = round(price_second - total_paid_second, 2)
                    html_content = render_to_string(
                        "basecamp/html_email-response-discrepancy.html",
                        {'name': second_post.name, 'price': price_second, 'paid': total_paid_second, 'diff': diff}
                    )
                    payment_send_email("Payment - EasyGo", html_content, [second_post.email, RECIPIENT_EMAIL])

                second_post.paid = total_paid_second
                second_post.reminder = True
                second_post.discount = ""
                second_post.save()

        else:
            html_content = render_to_string(
                "basecamp/html_email-noIdentity.html",
                {'name': instance.name, 'email': instance.email, 'amount': amount}
            )
            payment_send_email("Payment - EasyGo", html_content, [instance.email, RECIPIENT_EMAIL])


# Stripe > sending email & save
@shared_task
def notify_user_payment_stripe(instance_id):
    try:
        instance = StripePayment.objects.get(id=instance_id)
        logger.info(f"[Stripe] StripePayment instance fetched: ID={instance.id}, name={instance.name}, email={instance.email}, amount={instance.amount}")

        if not instance.name:
            logger.warning(f"[Stripe] instance.name is missing, skipping payment check.")
            return

        post_name = Post.objects.filter(
            Q(name__iregex=r'^%s$' % re.escape(instance.name)) |
            Q(email__iexact=instance.email)
        ).first()

        if not post_name:
            logger.warning(f"[Stripe] No matching Post found for name={instance.name}, email={instance.email}. Sending 'no identity' email.")
            html_content = render_to_string(
                "basecamp/html_email-noIdentity-stripe.html",
                {'name': instance.name, 'email': instance.email, 'amount': instance.amount}
            )
            payment_send_email("Payment - EasyGo", html_content, [instance.email, RECIPIENT_EMAIL])
            return

        # 첫 번째 Post 결제 처리
        already_paid = float(post_name.paid or 0)
        total_paid = already_paid + instance.amount
        price = float(post_name.price)

        if round(total_paid, 2) >= round(price, 2):
            logger.info(f"[Stripe] Full or over payment received for {post_name.name} (paid: {total_paid}, price: {price})")
            html_content = render_to_string(
                "basecamp/html_email-payment-success-stripe.html",
                {'name': post_name.name, 'email': post_name.email, 'amount': instance.amount}
            )
            payment_send_email("Payment - EasyGo", html_content, [post_name.email, RECIPIENT_EMAIL])
            post_name.toll = ""
            
        else:
            diff = round(price - total_paid, 2)
            logger.info(f"[Stripe] Short payment detected for {post_name.name} (paid: {total_paid}, price: {price}, diff: {diff})")
            post_name.toll = "short payment"
            html_content = render_to_string(
                "basecamp/html_email-response-discrepancy.html",
                {'name': post_name.name, 'price': price, 'paid': total_paid, 'diff': diff}
            )
            payment_send_email("Payment - EasyGo", html_content, [post_name.email, RECIPIENT_EMAIL])

        post_name.paid = total_paid
        post_name.reminder = True
        post_name.discount = ""
        post_name.save()
        logger.info(f"[Stripe] Post updated: ID={post_name.id}, paid={post_name.paid}")

        # Return ride 결제 처리
        if post_name.return_pickup_time == 'x':
            posts = Post.objects.filter(email=post_name.email)
            if len(posts) > 1:
                second_post = posts[1]
                already_paid_second = float(second_post.paid or 0)
                total_paid_second = already_paid_second + instance.amount
                price_second = float(second_post.price)

                if round(total_paid_second, 2) >= round(price_second, 2):
                    logger.info(f"[Stripe] Full/over payment for RETURN post: ID={second_post.id}")
                    html_content = render_to_string(
                        "basecamp/html_email-payment-success-stripe.html",
                        {'name': second_post.name, 'email': second_post.email, 'amount': instance.amount}
                    )
                    payment_send_email("Payment - EasyGo", html_content, [second_post.email, RECIPIENT_EMAIL])
                    second_post.toll = ""
                else:
                    diff = round(price_second - total_paid_second, 2)
                    logger.info(f"[Stripe] Short payment for RETURN post: ID={second_post.id}, diff={diff}")
                    second_post.toll = "short payment"
                    html_content = render_to_string(
                        "basecamp/html_email-response-discrepancy.html",
                        {'name': second_post.name, 'price': price_second, 'paid': total_paid_second, 'diff': diff}
                    )
                    payment_send_email("Payment - EasyGo", html_content, [second_post.email, RECIPIENT_EMAIL])

                second_post.paid = total_paid_second
                second_post.reminder = True
                second_post.discount = ""
                second_post.save()
                logger.info(f"[Stripe] RETURN Post updated: ID={second_post.id}, paid={second_post.paid}")
            else:
                logger.warning(f"[Stripe] Return ride requested but no second Post entry found for email={post_name.email}")

    except Exception as e:
        logger.exception(f"[Stripe] notify_user_payment_stripe failed: {str(e)}")


