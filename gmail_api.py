import os
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from datetime import timedelta, datetime, timezone
from django.conf import settings
from blog.models import Post  


SCOPES = ['https://www.googleapis.com/auth/gmail.send']
SERVICE_ACCOUNT_FILE = 'secure/reminder/service-account-file.json'
DELEGATED_USER_EMAIL = settings.RECIPIENT_EMAIL  

def create_message(sender, to, subject, message_text):
    """Create a message for an email."""
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def send_message(service, user_id, message):
    """Send an email message."""
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        return message
    except HttpError as error:
        print(f'An error occurred: {error}')

def send_apology_emails():
    """Send apology emails to customers created in the last year."""
    today = datetime.now(timezone.utc).date()
    start_date = today.replace(year=today.year - 1, month=10, day=23)
    end_date = today.replace(year=today.year - 1, month=11, day=23)

    customers = Post.objects.filter(created__range=[start_date, end_date])

    subject = 'Apology for Recent Email Error'
    message_text = (
        "Dear Valued Customer,\n\n"
        "I hope this message finds you well.\n\n"
        "We recently identified and fixed a system error that caused the loss of booking dates (flight_dates). "
        "We are in the process of recovering the lost information manually, but it is time-consuming, and some booking dates (pickup dates) may not be recoverable.\n\n"
        "We are reaching out individually to request this information. If you have not received such an email, it means we have successfully retrieved your information. "
        "However, if your booking date is approaching and you have not received a reminder notice, please contact us to confirm your details.\n\n"
        "We apologize for any inconvenience this may cause and appreciate your understanding. "
        "We are taking these steps to ensure no mistakes are made and to provide you with the best service possible.\n\n"         
        "Thank you for your understanding and patience.\n\n"
        "Best regards,\n\n"
        "Peter\n"
        "EasyGo Airport Shuttle\n"            
    )

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=DELEGATED_USER_EMAIL)

    try:
        service = build('gmail', 'v1', credentials=credentials)

        for customer in customers:
            to_email = customer.email
            message = create_message(DELEGATED_USER_EMAIL, to_email, subject, message_text)
            send_message(service, 'me', message)
            print(f'Email sent to {to_email}')

    except HttpError as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    send_apology_emails()
