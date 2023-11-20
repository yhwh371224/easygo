from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import base64
import os
import re
from .models import Post


GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    secure_directory = 'secure/'
    gmail_token_file_path = os.path.join(secure_directory, 'gmail_token.json')  

    
    if os.path.exists(gmail_token_file_path):
        creds = Credentials.from_authorized_user_file(gmail_token_file_path, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_file_path = os.path.join(secure_directory, 'gmail_credentials.json')
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)

        with open('gmail_token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def get_today_reminders(service, user_id='me', label_name='Re-reminder'):
    try:
        today = datetime.now().strftime('%Y/%m/%d')
        three_days_later = today + timedelta(days=3)

        labels = service.users().labels().list(userId=user_id).execute().get('labels', [])
        label_id = next((label['id'] for label in labels if label['name'] == label_name), None)

        if label_id:
            response = service.users().messages().list(userId=user_id, labelIds=[label_id], q=f'after:{today}').execute()
            messages = response.get('messages', [])

            for message in messages:
                msg = service.users().messages().get(userId=user_id, id=message['id']).execute()
                
                to_headers = [header['value'] for header in msg['payload']['headers'] if header['name'] == 'To']
                
                for receiver_email in to_headers:
                    filtered_posts = Post.objects.filter(email=receiver_email, created_at__range=[today, three_days_later])
            
                    if filtered_posts.exists():
                        for post in filtered_posts:
                            post.reminder = True
                            post.save()

        else:
            print(f"Label '{label_name}' not found.")

    except Exception as e:
        print(f'An error occurred: {e}')

if __name__ == '__main__':
    gmail_service = get_gmail_service()
    get_today_reminders(gmail_service)
