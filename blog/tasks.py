from .models import Post
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags 
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import date, timedelta


logger = get_task_logger(__name__)


@shared_task(bind=True)
def email_1(self, **kwargs):
    
    tomorrow_reminder = date.today() + timedelta(days=1)
    tomorrow_reminders = Post.objects.filter(flight_date=tomorrow_reminder)
    
    for reminder in tomorrow_reminders:
        
        if reminder.cancelled:           
            continue
        
        elif reminder.flight_date:
            html_content = render_to_string("basecamp/html_email-tomorrow.html", 
                {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
                'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 
                'street': reminder.street, 'suburb': reminder.suburb, 'price': reminder.price, 'meeting_point': reminder.meeting_point, 
                'driver': reminder.driver})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Reminder - tomorrow", text_content, '', [reminder.email])
            email.attach_alternative(html_content, "text/html")
            email.send()
            
        else:
            continue    
            
    return "1 day done"

    
@shared_task(bind=True)
def email_2(self, **kwargs):
    
    upcoming3_reminder = date.today() + timedelta(days=3)
    upcoming3_reminders = Post.objects.filter(flight_date=upcoming3_reminder)
    
    for reminder in upcoming3_reminders:
        
        if reminder.cancelled:           
            continue
        
        elif reminder.flight_date:
            html_content = render_to_string("basecamp/html_email-upcoming3.html", 
                {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
                'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 
                'street': reminder.street, 'suburb': reminder.suburb, 'price': reminder.price,  'meeting_point': reminder.meeting_point})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Reminder - 3days", text_content, '', [reminder.email])
            email.attach_alternative(html_content, "text/html")
            email.send()
            
        else:
            continue
            
    return "3 days done"


@shared_task(bind=True)
def email_3(self, **kwargs):
    
    upcoming7_reminder = date.today() + timedelta(days=7)
    upcoming7_reminders = Post.objects.filter(flight_date=upcoming7_reminder)

    for reminder in upcoming7_reminders:
        
        if reminder.cancelled:            
            continue
        
        elif reminder.flight_date:
            html_content = render_to_string("basecamp/html_email-upcoming7.html", 
                {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
                'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 'street': reminder.street, 'suburb': reminder.suburb})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Reminder - 7days", text_content, '', [reminder.email])
            email.attach_alternative(html_content, "text/html")
            email.send()
            
        else:
            continue
            
    return "7 days done"


@shared_task(bind=True)
def email_4(self, **kwargs):
    
    upcoming14_reminder = date.today() + timedelta(days=14)
    upcoming14_reminders = Post.objects.filter(flight_date=upcoming14_reminder)
    
    for reminder in upcoming14_reminders:
        
        if reminder.cancelled:            
            continue        
        
        elif reminder.flight_date:
            html_content = render_to_string("basecamp/html_email-upcoming14.html", 
                {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
                'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 
                'street': reminder.street, 'suburb': reminder.suburb, 'price': reminder.price})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Reminder - 2wks", text_content, '', [reminder.email])
            email.attach_alternative(html_content, "text/html")
            email.send()  
        
        else:
            continue 
                  
    return "14 days done"


@shared_task(bind=True)
def email_5(self, **kwargs):
     
    today_reminder = date.today()
    today_reminders = Post.objects.filter(flight_date=today_reminder)
    
    for reminder in today_reminders:
        
        if reminder.cancelled:            
            continue        
        
        elif reminder.flight_date:
            html_content = render_to_string("basecamp/html_email-today.html", 
                {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
                'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 
                'street': reminder.street, 'suburb': reminder.suburb, 'price': reminder.price, 'meeting_point': reminder.meeting_point,
                'driver': reminder.driver})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Notice - EasyGo", text_content, '', [reminder.email])
            email.attach_alternative(html_content, "text/html")
            email.send() 
            
        else:
            continue 
                   
    return "Today done"


@shared_task(bind=True)
def email_6(self, **kwargs):
    
    yesterday_reminder = date.today() + timedelta(days=-1)
    yesterday_reminders = Post.objects.filter(flight_date=yesterday_reminder)
    
    for reminder in yesterday_reminders:
        
        if reminder.cancelled:            
            continue        
        
        elif reminder.flight_date:
            html_content = render_to_string("basecamp/html_email-yesterday.html", 
                {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
                'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 'street': reminder.street, 'suburb': reminder.suburb})            
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Review - EasyGo", text_content, '', [reminder.email])
            email.attach_alternative(html_content, "text/html")
            email.send()
            
        else:         
            continue

    return "Yesterday done"


# @shared_task
# def send_email_delayed(name, contact, email, flight_date, flight_number, flight_time, pickup_time, direction,
#                        suburb, street, no_of_passenger, no_of_baggage, message, price, is_confirmed):    
        
#     html_content = render_to_string("basecamp/html_email-confirmation.html",
#                                     {'name': name, 'contact': contact, 'email': email,
#                                      'flight_date': flight_date, 'flight_number': flight_number,
#                                      'flight_time': flight_time, 'pickup_time': pickup_time,
#                                      'direction': direction, 'street': street, 'suburb': suburb,
#                                      'no_of_passenger': no_of_passenger, 'no_of_baggage': no_of_baggage,
#                                      'message': message, 'price': price, 'is_confirmed': is_confirmed })   
     
#     text_content = strip_tags(html_content)    
    
#     email = EmailMultiAlternatives(
#         "Booking confirmation - EasyGo",
#         text_content,
#         '',
#         [email, 'info@easygoshuttle.com.au']
#     )    
    
#     email.attach_alternative(html_content, "text/html")
    
#     email.send()      
