from .models import Post, Inquiry
from celery import shared_task
from django.core.mail import send_mail
from main.settings import RECIPIENT_EMAIL
from datetime import datetime, timedelta
from retrieve import main 
from celery.utils.log import get_task_logger
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import logging


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# logger for create_event_on_calendar
calendar_logger = logging.getLogger('blog.calendar')
calendar_logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(message)s')

logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'calendar.log'))
file_handler.setFormatter(formatter)

calendar_logger.addHandler(file_handler)

# logger for update_reminder
update_logger = logging.getLogger('blog.update_reminder')
update_logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(message)s')

logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'update_reminder.log'))
file_handler.setFormatter(formatter)

update_logger.addHandler(file_handler)


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
            calendar_logger.info('Event updated: %s', event.get('htmlLink'))

        except HttpError as error:
            calendar_logger.error('An error occurred while updating the event: %s', error)

    else:
        try:
            event = service.events().insert(calendarId='primary', body=event).execute()
            instance.calendar_event_id = event['id']  # Store the event ID in your model
            instance.save()
            calendar_logger.info('Event updated: %s', event.get('htmlLink'))

        except HttpError as error:
            calendar_logger.error('An error occurred while updating the event: %s', error)



@shared_task
def update_reminder():
    my_list = main()
    unique_emails = set()

    today = datetime.now()
    three_days_later = today + timedelta(days=3)

    for list_email in my_list:
        if list_email in unique_emails:
            continue
        else: 
            unique_emails.add(list_email)

            posts = Post.objects.filter(email__iexact=list_email, flight_date__range=[today, three_days_later])

            for post in posts:
                if post.reminder:
                    continue
                else: 
                    post.reminder = True
                    post.save()

                    update_logger.info(f'....Just now executed:{post.name}, {post.flight_date}, {post.pickup_time}')