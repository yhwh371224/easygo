from .models import Post
from celery import shared_task
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from main.settings import RECIPIENT_EMAIL
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import logging
import datetime 


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

formatter = logging.Formatter('%(asctime)s:%(message)s')

def configure_logger(name, filename):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(os.path.join(logs_dir, filename))
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


calendar_logger = configure_logger('blog.calendar', 'calendar.log')
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

    elif instance.cancelled:
        pass

    else:
        try:
            event = service.events().insert(calendarId='primary', body=event).execute()
            instance.calendar_event_id = event['id']  # Store the event ID in your model
            instance.save()
            calendar_logger.info('Event updated: %s', event.get('htmlLink'))

        except HttpError as error:
            calendar_logger.error('An error occurred while updating the event: %s', error)


logger_inquiry_local_email = configure_logger('blog.inquiry_local_email', 'inquiry_local_email.log')
@shared_task
def send_inquiry_exist_email(name, email, pickup_time, suburb, direction):
    content = f'''
    Hello, {name} \n
    Exist in Inquiry or Post *\n
    https://easygoshuttle.com.au 
    ============================
    Email: {email}
    Pickup: {pickup_time}
    Suburb: {suburb}
    Direction: {direction}
    ============================
    Best Regards,
    EasyGo Admin \n\n
    '''
    send_mail('', content, '', [RECIPIENT_EMAIL])
    logger_inquiry_local_email.info(f'Exist in Inquiry or Post email sent for {name} : {email}.')

@shared_task
def send_inquiry_non_exist_email(name, email, pickup_time, suburb, direction):
    content = f'''
    Hello, {name} \n
    Neither in Inquiry & Post *\n
    https://easygoshuttle.com.au     
    ============================
    Email: {email}
    Pickup: {pickup_time}
    Suburb: {suburb}
    Direction: {direction}
    ============================
    Best Regards,
    EasyGo Admin \n\n
    '''
    send_mail('', content, '', [RECIPIENT_EMAIL])
    logger_inquiry_local_email.info(f'Neither in Inquiry & Post email sent for {name} : {email}.')


logger_confirm_email = configure_logger('blog.confirm_email', 'confirm_email.log')
@shared_task
def send_confirm_email(name, contact, email, flight_date, return_flight_number):
    content = f'''
    {name}
    clicked the 'confirm booking' \n
    >> Sending email only! \n
    https://easygoshuttle.com.au/sending_email_first/ \n  
    https://easygoshuttle.com.au/sending_email_second/ \n
    ===============================
    Contact: {contact}
    Email: {email}
    Flight date: {flight_date}       
    Return flight number: {return_flight_number}
    ===============================\n        
    Best Regards,
    EasyGo Admin \n\n        
    '''
    send_mail('', content, '', [RECIPIENT_EMAIL])


logger_inquiry_response = configure_logger('blog.inquiry_response', 'inquiry_response.log')
@shared_task
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
        [email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()

    logger_inquiry_response.info(f'Inquiry response email sent for {name} on {flight_date}.')


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
        [email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()

    logger_inquiry_response.info(f'Inquiry cancelled email sent for {name} on {flight_date}.')