from __future__ import print_function
from main.settings import RECIPIENT_EMAIL
from .models import Post, Inquiry, Payment
from basecamp.models import Inquiry_point
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import re
from django.db.models import Q
# google calendar 
import os.path
import os 
import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# Flight return booking
@receiver(post_save, sender=Post)
def notify_user_post(sender, instance, created, **kwargs):
    if not instance.calendar_event_id and instance.return_flight_number:
        p = Post(name=instance.name, contact=instance.contact, email=instance.email, company_name=instance.company_name, email1=instance.email1, 
                 flight_date=instance.return_flight_date, flight_number=instance.return_flight_number, flight_time=instance.return_flight_time, 
                 pickup_time=instance.return_pickup_time, direction=instance.return_direction, suburb=instance.suburb, street=instance.street, 
                 no_of_passenger=instance.no_of_passenger, no_of_baggage=instance.no_of_baggage, message=instance.message, return_pickup_time="x",
                 return_flight_date=instance.flight_date, notice=instance.notice, price=instance.price, paid=instance.paid, driver=instance.driver)
        p.save() 
    
    
# Flight inquiry
@receiver(post_save, sender=Inquiry)
def notify_user_inquiry(sender, instance, created, **kwargs):
    if instance.cancelled:
        html_content = render_to_string("basecamp/html_email-cancelled.html",
                                        {'name': instance.name, 'email': instance.email,
                                         })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "Booking Inquiry - EasyGo",
            text_content,
            '',
            [instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    elif instance.is_confirmed:    
        html_content = render_to_string("basecamp/html_email-inquiry-response.html",
                                        {'company_name': instance.company_name, 'name': instance.name, 'contact': instance.contact, 'email': instance.email,
                                         'flight_date': instance.flight_date, 'flight_number': instance.flight_number,
                                         'flight_time': instance.flight_time, 'pickup_time': instance.pickup_time,
                                         'direction': instance.direction, 'street': instance.street, 'suburb': instance.suburb,
                                         'no_of_passenger': instance.no_of_passenger, 'no_of_baggage': instance.no_of_baggage,
                                         'return_direction': instance.return_direction, 'return_flight_date': instance.return_flight_date, 
                                         'return_flight_number': instance.return_flight_number, 'return_flight_time': instance.return_flight_time,
                                         'return_pickup_time': instance.return_pickup_time, 'message': instance.message, 'price': instance.price, 
                                         'notice': instance.notice, 'private_ride': instance.private_ride,})
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "Booking Inquiry - EasyGo",
            text_content,
            '',
            [instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()


# Point to point inquiry
@receiver(post_save, sender=Inquiry_point)
def notify_user_inquiry_point(sender, instance, created, **kwargs):
    if instance.cancelled:
        html_content = render_to_string("basecamp/html_email-cancelled.html",
                                        {'name': instance.name, 'email': instance.email,
                                         })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "Booking Inquiry - EasyGo",
            text_content,
            '',
            [instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    elif instance.is_confirmed:    
        html_content = render_to_string("basecamp/html_email-inquiry-response-p2p.html",
                                        {'name': instance.name, 'contact': instance.contact, 'email': instance.email,
                                         'flight_date': instance.flight_date, 'pickup_time': instance.pickup_time, 'flight_number': instance.flight_number,
                                         'street': instance.street, 'no_of_passenger': instance.no_of_passenger, 'no_of_baggage': instance.no_of_baggage,                                         
                                         'return_flight_date': instance.return_flight_date, 'return_flight_number': instance.return_flight_number, 
                                         'return_pickup_time': instance.return_pickup_time, 'message': instance.message, 'price': instance.price, 
                                         'notice': instance.notice, 'private_ride': instance.private_ride,})
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "Booking Inquiry - EasyGo",
            text_content,
            '',
            [instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()      


# PayPal Payment & Google Calendar payment update
# If modifying these scopes, delete the file token.json.

@receiver(post_save, sender=Payment)
def notify_user_payment(sender, instance, created, **kwargs):      
    post_name = Post.objects.filter(Q(name__iregex=r'^%s$' % re.escape(instance.item_name)) | Q(email=instance.payer_email)).first()
    
    if post_name: 
        post_name.paid = instance.gross_amount
        post_name.save()         
        
        html_content = render_to_string("basecamp/html_email-payment-success.html",
                                    {'name': instance.item_name, 'email': instance.payer_email,
                                     'amount': instance.gross_amount })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "PayPal payment - EasyGo",
            text_content,
            '',
            [instance.payer_email, RECIPIENT_EMAIL]
        )        
        email.attach_alternative(html_content, "text/html")        
        email.send()


        if post_name.return_pickup_time == 'x':
                post_name_second = Post.objects.filter(email=post_name.email)[1]
                post_name_second.paid = instance.gross_amount
                post_name_second.save()
     
            
    else:
        html_content = render_to_string("basecamp/html_email-noIdentity.html",
                                    {'name': instance.item_name, 'email': instance.payer_email,
                                     'amount': instance.gross_amount })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "PayPal payment - EasyGo",
            text_content,
            '',
            [instance.payer_email, RECIPIENT_EMAIL]
        )        
        email.attach_alternative(html_content, "text/html")        
        email.send()
    


## google calendar recording 
@receiver(post_save, sender=Post)
def create_event_on_calendar(sender, instance, created, **kwargs):
    
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
    
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    
        
            service = build('calendar', 'v3', credentials=creds)        
            
            paid_str = f'paid' if instance.paid else ''
            reminder_str = f'!' if instance.reminder else ''

            title = " ".join([reminder_str, instance.pickup_time, instance.flight_number, instance.flight_time, 'p'+str(instance.no_of_passenger), paid_str, '$'+instance.price, instance.contact])
            address = " ".join([instance.street, instance.suburb])            
            if instance.return_flight_number:
                message = " ".join([instance.name, instance.email, 'b'+instance.no_of_baggage, 'm:'+instance.message, "d:"+str(instance.return_flight_date)])
            else:
                message = " ".join([instance.name, instance.email, 'b'+instance.no_of_baggage, 'm:'+instance.message])
            flight_date = datetime.datetime.strptime(str(instance.flight_date), '%Y-%m-%d')
            pickup_time = datetime.datetime.strptime(instance.pickup_time, '%H:%M')
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
                print('Event updated: %s' % (event.get('htmlLink')))
            except HttpError as error:
                print(f'An error occurred while updating the event: {error}')
        else:
            try:
                event = service.events().insert(calendarId='primary', body=event).execute()
                instance.calendar_event_id = event['id']  # Store the event ID in your model
                instance.save()
                print('Event created: %s' % (event.get('htmlLink')))
            except HttpError as error:
                print(f'An error occurred while creating the event: {error}')
