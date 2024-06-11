import datetime
import os

from googleapiclient.discovery import build
from google.oauth2 import service_account
from django.core.mail import send_mail
from celery import shared_task
from main.settings import RECIPIENT_EMAIL, DEFAULT_FROM_EMAIL
from .models import Post


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@shared_task
def create_event_on_calendar(instance_id):    
    # Fetch the Post instance
    instance = Post.objects.get(pk=instance_id)

    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'secure/calendar/calendar-service-account-file.json'
    DELEGATED_USER_EMAIL = RECIPIENT_EMAIL  # 위임받은 사용자의 이메일 주소

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=DELEGATED_USER_EMAIL)

    service = build('calendar', 'v3', credentials=credentials)        
    
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
    '''
    send_mail(flight_date, content, DEFAULT_FROM_EMAIL, [RECIPIENT_EMAIL])


# Clicked confirm_booking form 
@shared_task
def send_email_task(flight_date, direction, suburb, no_of_passenger):
    content = f'''
    someone checked the price from homepage \n    
    ============================= \n    
    flight date:  {flight_date}  \n
    Direction: {direction} \n 
    Suburbs: {suburb} \n
    No of Pax: {no_of_passenger}\n
    ===============================\n          
    '''
    send_mail(flight_date, content, DEFAULT_FROM_EMAIL, [RECIPIENT_EMAIL])


# Review page
@shared_task
def send_notification_email(RECIPIENT_EMAIL):
    send_mail(
        'Reviews Accessed',
        'A user has accessed the reviews page.',
        DEFAULT_FROM_EMAIL,
        [RECIPIENT_EMAIL],
        fail_silently=False,
    )


# Suburbs page 
@shared_task
def send_notice_email(RECIPIENT_EMAIL):
    send_mail(
        'Suburbs Accessed',
        'A user has accessed the suburbs page.',
        DEFAULT_FROM_EMAIL,
        [RECIPIENT_EMAIL],
        fail_silently=False,
    )



