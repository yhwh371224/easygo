import datetime
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from django.core.mail import send_mail
from celery import shared_task
from main.settings import RECIPIENT_EMAIL
from .models import Post


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@shared_task
def create_event_on_calendar(instance_id):    
    # Fetch the Post instance
    instance = Post.objects.get(pk=instance_id)

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    creds = None
    secure_directory = 'secure/calendar/'
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
    pending_str = f'?' if instance.discount else ''
    cancelled_str = f'c' if instance.cancelled else ''    
    title = " ".join([cancelled_str, reminder_str, pending_str, instance.pickup_time, instance.flight_number, 
                      instance.flight_time, 'p'+str(instance.no_of_passenger), 
                      paid_str, '$'+instance.price, instance.contact])
    address = " ".join([instance.street, instance.suburb])        
    message_parts = [instance.name, instance.email, 
                     'b'+str(instance.no_of_baggage) if instance.no_of_baggage is not None else '', 
                     'm:'+instance.message if instance.message is not None else '', 
                     'n:'+instance.notice if instance.notice is not None else '', 
                     "d:"+str(instance.return_flight_date), 
                     '$'+str(instance.paid) if instance.paid is not None else '']
    message = " ".join(filter(None, message_parts))            
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
def send_confirm_email(name, email, flight_date, return_flight_number):
    content = f'''
    {name}
    clicked the 'confirm booking' \n
    >> Sending email only! \n
    https://easygoshuttle.com.au/sending_email_first/ \n  
    https://easygoshuttle.com.au/sending_email_second/ \n
    ============================= \n    
    Email:  {email}  \n
    Flight date: {flight_date} \n 
    Return flight number: {return_flight_number}
    ===============================\n        
    Best Regards, \n
    EasyGo Admin \n\n        
    '''
    send_mail(flight_date, content, '', [RECIPIENT_EMAIL])
