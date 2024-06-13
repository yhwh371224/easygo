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

    cancelled_str = 'c' if instance.cancelled else ''
    reminder_str = '!' if instance.reminder else ''
    pending_str = '?' if instance.discount else ''
    pickup_time_str = instance.pickup_time or ''
    flight_number_str = instance.flight_number or ''
    flight_time_str = instance.flight_time or ''
    no_of_passenger_str = f'p{instance.no_of_passenger}' if instance.no_of_passenger is not None else ''
    paid_str = 'paid' if instance.paid else ''    
    price_str = f'${instance.price}' if instance.price is not None else ''
    contact_str = instance.contact or ''

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

    address = " ".join([instance.street, instance.suburb])        
    message_parts = [instance.name, instance.email, 
                     'b:'+str(instance.no_of_baggage) if instance.no_of_baggage is not None else '', 
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
    https://easygoshuttle.com.au/sending_email_second/
    =============================   
    Email:  {email}
    Flight date: {flight_date}
    Return flight number: {return_flight_number}
    ===============================          
    '''
    send_mail(flight_date, content, DEFAULT_FROM_EMAIL, [RECIPIENT_EMAIL])


# Home page for price 
@shared_task
def send_email_task(flight_date, direction, suburb, no_of_passenger):
    content = f'''
    someone checked the price from homepage    
    =============================  
    flight date:  {flight_date}
    Direction: {direction}
    Suburbs: {suburb}
    No of Pax: {no_of_passenger}
    ===============================        
    '''
    send_mail(flight_date, content, DEFAULT_FROM_EMAIL, [RECIPIENT_EMAIL])


# Review page, suburbs page, service, information, about_us, terms, policy 
@shared_task
def send_notice_email(subject, message, RECIPIENT_EMAIL):
    send_mail(
        subject,
        message,
        DEFAULT_FROM_EMAIL,
        [RECIPIENT_EMAIL],
        fail_silently=False,
    )





