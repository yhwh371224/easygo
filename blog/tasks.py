import datetime
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
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
    cancelled_str = f'c' if instance.cancelled else ''
    title = " ".join([cancelled_str, reminder_str, instance.pickup_time, instance.flight_number, 
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
    

# Inquiry response email 
def send_inquiry_confirmed_email(instance_data):
    company_name = instance_data.get('company_name', '')
    name = instance_data.get('name', '')
    contact = instance_data.get('contact', '')
    email = instance_data.get('email', '')
    flight_date = instance_data.get('flight_date', '')
    flight_number = instance_data.get('flight_number', '')
    flight_time = instance_data.get('flight_time', '')
    pickup_time = instance_data.get('pickup_time', '')
    direction = instance_data.get('direction', '')
    street = instance_data.get('street', '')
    suburb = instance_data.get('suburb', '')
    no_of_passenger = instance_data.get('no_of_passenger', '')
    no_of_baggage = instance_data.get('no_of_baggage', '')
    return_direction = instance_data.get('return_direction', '')
    return_flight_date = instance_data.get('return_flight_date', '')
    return_flight_number = instance_data.get('return_flight_number', '')
    return_flight_time = instance_data.get('return_flight_time', '')
    return_pickup_time = instance_data.get('return_pickup_time', '')
    message = instance_data.get('message', '')
    price = instance_data.get('price', '')
    notice = instance_data.get('notice', '')
    private_ride = instance_data.get('private_ride', '')

    
    html_content = render_to_string("basecamp/html_email-inquiry-response.html",
                                        {'company_name': company_name, 'name': name, 'contact': contact, 'email': email,
                                         'flight_date': flight_date, 'flight_number': flight_number,
                                         'flight_time': flight_time, 'pickup_time': pickup_time,
                                         'direction': direction, 'street': street, 'suburb': suburb,
                                         'no_of_passenger': no_of_passenger, 'no_of_baggage': no_of_baggage,
                                         'return_direction': return_direction, 'return_flight_date': return_flight_date, 
                                         'return_flight_number': return_flight_number, 'return_flight_time': return_flight_time,
                                         'return_pickup_time': return_pickup_time, 'message': message, 'price': price, 
                                         'notice': notice, 'private_ride': private_ride,})
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        "EasyGo Booking Inquiry",
        text_content,
        '',
        [email, RECIPIENT_EMAIL]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


@shared_task
def send_inquiry_cancelled_email(instance_data):
    company_name = instance_data.get('company_name', '')
    name = instance_data.get('name', '')
    contact = instance_data.get('contact', '')
    email = instance_data.get('email', '')
    flight_date = instance_data.get('flight_date', '')
    flight_number = instance_data.get('flight_number', '')
    flight_time = instance_data.get('flight_time', '')
    pickup_time = instance_data.get('pickup_time', '')
    direction = instance_data.get('direction', '')
    street = instance_data.get('street', '')
    suburb = instance_data.get('suburb', '')
    no_of_passenger = instance_data.get('no_of_passenger', '')
    no_of_baggage = instance_data.get('no_of_baggage', '')
    return_direction = instance_data.get('return_direction', '')
    return_flight_date = instance_data.get('return_flight_date', '')
    return_flight_number = instance_data.get('return_flight_number', '')
    return_flight_time = instance_data.get('return_flight_time', '')
    return_pickup_time = instance_data.get('return_pickup_time', '')
    message = instance_data.get('message', '')
    price = instance_data.get('price', '')
    notice = instance_data.get('notice', '')
    private_ride = instance_data.get('private_ride', '')

    
    html_content = render_to_string("basecamp/html_email-cancelled.html",
                                        {'company_name': company_name, 'name': name, 'contact': contact, 'email': email,
                                         'flight_date': flight_date, 'flight_number': flight_number,
                                         'flight_time': flight_time, 'pickup_time': pickup_time,
                                         'direction': direction, 'street': street, 'suburb': suburb,
                                         'no_of_passenger': no_of_passenger, 'no_of_baggage': no_of_baggage,
                                         'return_direction': return_direction, 'return_flight_date': return_flight_date, 
                                         'return_flight_number': return_flight_number, 'return_flight_time': return_flight_time,
                                         'return_pickup_time': return_pickup_time, 'message': message, 'price': price, 
                                         'notice': notice, 'private_ride': private_ride,})
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        "EasyGo Booking Inquiry",
        text_content,
        '',
        [email, RECIPIENT_EMAIL]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


