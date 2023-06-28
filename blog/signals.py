from __future__ import print_function
from .models import Post, Inquiry, Payment
from basecamp.models import Inquiry_point
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import re
from django.db.models import Q
# # google calendar 
# import os.path
# from decouple import config
# from datetime import date, timedelta
# import datetime
# # google api
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request
# from googleapiclient import errors
# from googleapiclient.errors import HttpError


# Flight return booking
@receiver(post_save, sender=Post)
def notify_user_post(sender, instance, created, **kwargs):
    if not instance.paid and instance.return_flight_number:
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
        

# PayPal Payment
@receiver(post_save, sender=Payment)
def notify_user_payment(sender, instance, created, **kwargs):      
    post_name = Post.objects.filter(Q(email=instance.payer_email) | Q(name__iregex=r'^%s$' % re.escape(instance.item_name))).first()
    
    if post_name: 
        post_name.paid = instance.gross_amount
        post_name.save() 
        
        html_content = render_to_string("basecamp/html_email-payment-success.html",
                                    {'name': instance.item_name, 'email': instance.payer_email,
                                     'amount': instance.gross_amount, 'flight_date': post_name.flight_date, 
                                     'return_flight_date': post_name.return_flight_date, 
                                     'return_pickup_time': post_name.return_pickup_time, })
        
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "PayPal payment - EasyGo",
            text_content,
            '',
            [instance.payer_email, 'info@easygoshuttle.com.au']
        )        
        email.attach_alternative(html_content, "text/html")        
        email.send()               

        if post_name.return_pickup_time == "x":        
            post_name1 = Post.objects.filter(Q(email=instance.payer_email) | Q(name__iregex=r'^%s$' % re.escape(instance.item_name)))[1]
            post_name1.paid = instance.gross_amount
            post_name1.save()
            
    else:
        html_content = render_to_string("basecamp/html_email-noIdentity.html",
                                    {'name': instance.item_name, 'email': instance.payer_email,
                                     'amount': instance.gross_amount })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "PayPal payment - EasyGo",
            text_content,
            '',
            [instance.payer_email, 'info@easygoshuttle.com.au']
        )        
        email.attach_alternative(html_content, "text/html")        
        email.send()
        
        
# # If modifying these scopes, delete the file token.json.
# SCOPES = ['https://www.googleapis.com/auth/calendar']


# @receiver(post_save, sender=Post)
# def create_event_on_calendar(sender, instance, created, **kwargs):
#     creds = None
#     # The file token.json stores the user's access and refresh tokens, and is
#     # created automatically when the authorization flow completes for the first
#     # time.
#     if os.path.exists('token.json'):
#         creds = Credentials.from_authorized_user_file('token.json', SCOPES)    
#     # If there are no (valid) credentials available, let the user log in.
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 'credentials.json', SCOPES)
#             creds = flow.run_local_server(port=0)
#         # Save the credentials for the next run
#         with open('token.json', 'w') as token:
#             token.write(creds.to_json())
   
#     service = build('calendar', 'v3', credentials=creds)
   
#     if created:
#         # Create a Google Calendar API service object
#         service = build('calendar', 'v3', credentials=creds)        
#         # Call the funtion that creates the event in Google Calendar
#         title = " ".join([instance.pickup_time, instance.flight_number, instance.flight_time, 'p'+str(instance.no_of_passenger), '$'+instance.price, instance.contact])
#         address = " ".join([instance.street, instance.suburb])
#         message = " ".join([instance.name, instance.email, instance.no_of_baggage, instance.message, str(instance.return_flight_date)])
#         flight_date = instance.flight_date # if flight_date is 'Charfield', not Datefield, then > datetime.datetime.strptime(instance.flight_date, '%Y-%m-%d') 
#         pickup_time = datetime.datetime.strptime(instance.pickup_time, '%H:%M')
#         start = datetime.datetime.combine(flight_date, pickup_time.time())        
#         end = start + datetime.timedelta(hours=1)


#         event = {
#             'summary': title,
#             'location': address,
#             'start': {
#                 'dateTime': start.strftime('%Y-%m-%dT%H:%M:%S'),
#                 'timeZone': 'Australia/Sydney',
#             },
#             'end': {
#                 'dateTime': end.strftime('%Y-%m-%dT%H:%M:%S'),
#                 'timeZone': 'Australia/Sydney',
#             },
#             'description': message,
#         }   
        
#     try:
#         event = service.events().insert(calendarId='primary', body=event).execute()        
#         print('Event created: %s' % (event.get('htmlLink')))
       
#     except HttpError as error:
#         print(f'An error occurred: {error}')
