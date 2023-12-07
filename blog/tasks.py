from .models import Post, Driver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags 
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import date, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import datetime


logger = get_task_logger(__name__)


@shared_task
def create_event_on_calendar(instance_id):
    # Fetch the Post instance
    instance = Post.objects.get(pk=instance_id)

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    creds = None
    secure_directory = 'secure/'
    token_file_path = os.path.join(secure_directory, 'token.json')

    if os.path.exists(token_file_path):
        creds = Credentials.from_authorized_user_file(token_file_path, SCOPES)   

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            
        else:
            credentials_file_path = os.path.join(secure_directory, 'credentials.json')
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file_path, 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)        
    
    paid_str = f'paid' if instance.paid else ''
    reminder_str = f'!' if instance.reminder else ''
    title = " ".join([reminder_str, instance.pickup_time, instance.flight_number, instance.flight_time, 'p'+str(instance.no_of_passenger), paid_str, '$'+instance.price, instance.contact])
    address = " ".join([instance.street, instance.suburb])            
    message = " ".join([instance.name, instance.email, 'b'+instance.no_of_baggage, 'm:'+instance.message, 'n:'+instance.notice, "d:"+str(instance.return_flight_date), '$'+instance.paid])            
    flight_date = datetime.datetime.strptime(str(instance.flight_date), '%Y-%m-%d')

    if instance.pickup_time:
        pickup_time = datetime.datetime.strptime(instance.pickup_time, '%H:%M')

    else:
        pickup_time = datetime.datetime.strptime('00:00', '%H:%M') 
    start = datetime.datetime.combine(flight_date, pickup_time.time())        
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
    if instance.calendar_event_id:            
        try:
            event = service.events().update(calendarId='primary', eventId=instance.calendar_event_id, body=event).execute()
            logger.info('Event updated: %s', event.get('htmlLink'))

        except HttpError as error:
            logger.error('An error occurred while updating the event: %s', error)

    else:
        try:
            event = service.events().insert(calendarId='primary', body=event).execute()
            instance.calendar_event_id = event['id']  # Store the event ID in your model
            instance.save()
            logger.info('Event updated: %s', event.get('htmlLink'))
            
        except HttpError as error:
            logger.error('An error occurred while updating the event: %s', error)







# @shared_task(bind=True)
# def email_1(self, **kwargs):
    
#     tomorrow_reminder = date.today() + timedelta(days=1)
#     tomorrow_reminders = Post.objects.filter(flight_date=tomorrow_reminder)
    
#     for reminder in tomorrow_reminders:
        
#         if reminder.cancelled:           
#             continue
        
#         elif reminder.flight_date:
#             html_content = render_to_string("basecamp/html_email-tomorrow.html", 
#                 {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
#                 'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 
#                 'street': reminder.street, 'suburb': reminder.suburb, 'price': reminder.price, 'meeting_point': reminder.meeting_point, 
#                 'driver': reminder.driver})
#             text_content = strip_tags(html_content)
#             email = EmailMultiAlternatives("Reminder tomorrow", text_content, '', [reminder.email])
#             email.attach_alternative(html_content, "text/html")
#             email.send()
            
#         else:
#             continue    
            
#     return "1 day done"

    
# @shared_task(bind=True)
# def email_2(self, **kwargs):
    
#     upcoming3_reminder = date.today() + timedelta(days=3)
#     upcoming3_reminders = Post.objects.filter(flight_date=upcoming3_reminder)
    
#     for reminder in upcoming3_reminders:
        
#         if reminder.cancelled:           
#             continue
        
#         elif reminder.flight_date:
#             html_content = render_to_string("basecamp/html_email-upcoming3.html", 
#                 {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
#                 'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 
#                 'street': reminder.street, 'suburb': reminder.suburb, 'price': reminder.price,  'meeting_point': reminder.meeting_point})
#             text_content = strip_tags(html_content)
#             email = EmailMultiAlternatives("Reminder 3days", text_content, '', [reminder.email])
#             email.attach_alternative(html_content, "text/html")
#             email.send()
            
#         else:
#             continue
            
#     return "3 days done"


# @shared_task(bind=True)
# def email_3(self, **kwargs):
    
#     upcoming7_reminder = date.today() + timedelta(days=7)
#     upcoming7_reminders = Post.objects.filter(flight_date=upcoming7_reminder)

#     for reminder in upcoming7_reminders:
        
#         if reminder.cancelled:            
#             continue
        
#         elif reminder.flight_date:
#             html_content = render_to_string("basecamp/html_email-upcoming7.html", 
#                 {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
#                 'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 'street': reminder.street, 'suburb': reminder.suburb})
#             text_content = strip_tags(html_content)
#             email = EmailMultiAlternatives("Reminder 7days", text_content, '', [reminder.email])
#             email.attach_alternative(html_content, "text/html")
#             email.send()
            
#         else:
#             continue
            
#     return "7 days done"


# @shared_task(bind=True)
# def email_4(self, **kwargs):
    
#     upcoming14_reminder = date.today() + timedelta(days=14)
#     upcoming14_reminders = Post.objects.filter(flight_date=upcoming14_reminder)
    
#     for reminder in upcoming14_reminders:
        
#         if reminder.cancelled:            
#             continue        
        
#         elif reminder.flight_date:
#             html_content = render_to_string("basecamp/html_email-upcoming14.html", 
#                 {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
#                 'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 
#                 'street': reminder.street, 'suburb': reminder.suburb, 'price': reminder.price})
#             text_content = strip_tags(html_content)
#             email = EmailMultiAlternatives("Reminder 2wks", text_content, '', [reminder.email])
#             email.attach_alternative(html_content, "text/html")
#             email.send()  
        
#         else:
#             continue 
                  
#     return "14 days done"


# @shared_task(bind=True)
# def email_5(self, **kwargs):
     
#     today_reminder = date.today()
#     today_reminders = Post.objects.filter(flight_date=today_reminder)
    
#     for reminder in today_reminders:
        
#         if reminder.cancelled:            
#             continue        
        
#         elif reminder.flight_date:            
#             driver_instance = reminder.driver            
             
#             driver_name = driver_instance.driver_name
#             driver_contact = driver_instance.driver_contact
#             driver_plate = driver_instance.driver_plate
#             driver_car = driver_instance.driver_car

#             html_content = render_to_string("basecamp/html_email-today.html", 
#                 {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
#                 'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 
#                 'street': reminder.street, 'suburb': reminder.suburb, 'price': reminder.price, 'meeting_point': reminder.meeting_point,
#                 'driver_name': driver_name, 'driver_contact': driver_contact, 'driver_plate': driver_plate, 'driver_car': driver_car})
#             text_content = strip_tags(html_content)
#             email = EmailMultiAlternatives("Reminder today", text_content, '', [reminder.email])
#             email.attach_alternative(html_content, "text/html")
#             email.send() 
            
#         else:
#             continue 
                   
#     return "Today done"


# @shared_task(bind=True)
# def email_6(self, **kwargs):
    
#     yesterday_reminder = date.today() + timedelta(days=-1)
#     yesterday_reminders = Post.objects.filter(flight_date=yesterday_reminder)
    
#     for reminder in yesterday_reminders:
        
#         if reminder.cancelled:            
#             continue        
        
#         elif reminder.flight_date:
#             html_content = render_to_string("basecamp/html_email-yesterday.html", 
#                 {'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number, 
#                 'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time, 'street': reminder.street, 'suburb': reminder.suburb})            
#             text_content = strip_tags(html_content)
#             email = EmailMultiAlternatives("Review - reminder", text_content, '', [reminder.email])
#             email.attach_alternative(html_content, "text/html")
#             email.send()
            
#         else:         
#             continue

#     return "Yesterday done"


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
