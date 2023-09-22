from __future__ import print_function
from blog.models import Post
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.html import strip_tags
# google calendar 
import os.path
import os 
from datetime import datetime, date
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def create_event_on_calendar():
    today = date.today()
    posts_created_today = Post.objects.filter(created__date=today)
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
   
    service = build('calendar', 'v3', credentials=creds)

     # Iterate through each Post created today and create events
    for post in posts_created_today:        
        # Create a Google Calendar API service object
        service = build('calendar', 'v3', credentials=creds)        
        # Call the funtion that creates the event in Google Calendar
        title = " ".join([post.pickup_time, post.flight_number,     post.flight_time, 'p'+str(post.no_of_passenger), '$'+post.price, post.contact])
        address = " ".join([post.street, post.suburb])
        message = " ".join([post.name, post.email, post.no_of_baggage, post.message])
        flight_date = datetime.datetime.strptime(str(post.flight_date), '%Y-%m-%d')
        pickup_time = datetime.datetime.strptime(post.pickup_time, '%H:%M')
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

        try:
            event = service.events().insert(calendarId='primary', body=event).execute()        
            print('Event created: %s' % (event.get('htmlLink')))

        except HttpError as error:
            print(f'An error occurred: {error}')
