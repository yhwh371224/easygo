from .models import Post
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags 
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import date, datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
from time import sleep



logger = get_task_logger(__name__)

today = date.today()
reminder_1day = today + timedelta(days=1)
reminders_1day = Post.objects.filter(flight_date=reminder_1day)

reminder_3days = today + timedelta(days=3)
reminders_3days = Post.objects.filter(flight_date=reminder_3days)

reminder_7days = today + timedelta(days=7)
reminders_7days = Post.objects.filter(flight_date=reminder_7days)

reminder_14days = today + timedelta(days=14)
reminders_14days = Post.objects.filter(flight_date=reminder_14days)

reminder_today = today
reminders_today = Post.objects.filter(flight_date=reminder_today)

reminder_yesterday = today + timedelta(days=-1)
reminders_yesterday = Post.objects.filter(flight_date=reminder_yesterday)


@shared_task(bind=True)
def email_1(self, **kwargs):    
    for i in reminders_1day:
        if i.flight_date:
            html_content = render_to_string("basecamp/html_email-tomorrow.html", 
            {'name': i.name, 'flight_date': i.flight_date, 'flight_number': i.flight_number, 
            'flight_time': i.flight_time, 'direction': i.direction, 'pickup_time': i.pickup_time, 'street': i.street, 'suburb': i.suburb})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Reminder - Booking", text_content, '', [i.email])
            email.attach_alternative(html_content, "text/html")
            email.send()

        else:
            print ("No bookings - 1 day")

    return "1 day done"

    
@shared_task(bind=True)
def email_2(self, **kwargs):    
    for i in reminders_3days:
        if i.flight_date:
            html_content = render_to_string("basecamp/html_email-upcoming3.html", 
            {'name': i.name, 'flight_date': i.flight_date, 'flight_number': i.flight_number, 
            'flight_time': i.flight_time, 'direction': i.direction, 'pickup_time': i.pickup_time, 'street': i.street, 'suburb': i.suburb})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Reminder - Booking", text_content, '', [i.email])
            email.attach_alternative(html_content, "text/html")
            email.send()

        else:
            print ("No bookings - 3 days")

    return "3 days done"


@shared_task(bind=True)
def email_3(self, **kwargs):    
    for i in reminders_7days:
        if i.flight_date:
            html_content = render_to_string("basecamp/html_email-upcoming7.html", 
            {'name': i.name, 'flight_date': i.flight_date, 'flight_number': i.flight_number, 
            'flight_time': i.flight_time, 'direction': i.direction, 'pickup_time': i.pickup_time, 'street': i.street, 'suburb': i.suburb})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Reminder - Booking", text_content, '', [i.email])
            email.attach_alternative(html_content, "text/html")
            email.send()
            
        else:
            print ("No bookings - 7 days")

    return "7 days done"


@shared_task(bind=True)
def email_4(self, **kwargs):    
    for i in reminders_14days:
        if i.flight_date:
            html_content = render_to_string("basecamp/html_email-upcoming14.html", 
            {'name': i.name, 'flight_date': i.flight_date, 'flight_number': i.flight_number, 
            'flight_time': i.flight_time, 'direction': i.direction, 'pickup_time': i.pickup_time, 'street': i.street, 'suburb': i.suburb})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Reminder - Booking", text_content, '', [i.email])
            email.attach_alternative(html_content, "text/html")
            email.send()

        else:
            print ("No bookings - 14 days")

    return "14 days done"


@shared_task(bind=True)
def email_5(self, **kwargs):    
    for i in reminders_today:
        if i.flight_date:
            html_content = render_to_string("basecamp/html_email-today.html", 
            {'name': i.name, 'flight_date': i.flight_date, 'flight_number': i.flight_number, 
            'flight_time': i.flight_time, 'direction': i.direction, 'pickup_time': i.pickup_time, 'street': i.street, 'suburb': i.suburb})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Notice - EasyGo", text_content, '', [i.email])
            email.attach_alternative(html_content, "text/html")
            email.send()

        else:
            print ("No bookings - today")

    return "Today done"


@shared_task(bind=True)
def email_6(self, **kwargs):    
    for i in reminders_yesterday:
        if i.flight_date:
            html_content = render_to_string("basecamp/html_email-yesterday.html", 
            {'name': i.name, 'flight_date': i.flight_date, 'flight_number': i.flight_number, 
            'flight_time': i.flight_time, 'direction': i.direction, 'pickup_time': i.pickup_time, 'street': i.street, 'suburb': i.suburb})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Review - EasyGo", text_content, '', ['info@easygoshuttle.com.au'])
            email.attach_alternative(html_content, "text/html")
            email.send()

        else:
            print ("No bookings - yesterday")

    return "Yesterday done"


@shared_task
def send_email_delayed(name, contact, email, flight_date, flight_number, flight_time, pickup_time, direction,
                       suburb, street, no_of_passenger, no_of_baggage, message, price, is_confirmed):    
    #sleep(180)       
    html_content = render_to_string("basecamp/html_email-confirmation.html",
                                    {'name': name, 'contact': contact, 'email': email,
                                     'flight_date': flight_date, 'flight_number': flight_number,
                                     'flight_time': flight_time, 'pickup_time': pickup_time,
                                     'direction': direction, 'street': street, 'suburb': suburb,
                                     'no_of_passenger': no_of_passenger, 'no_of_baggage': no_of_baggage,
                                     'message': message, 'price': price, 'is_confirmed': is_confirmed })    
    text_content = strip_tags(html_content)    
    email = EmailMultiAlternatives(
        "Booking confirmation - EasyGo",
        text_content,
        '',
        [email, 'info@easygoshuttle.com.au']
    )    
    email.attach_alternative(html_content, "text/html")
    email.send()      
