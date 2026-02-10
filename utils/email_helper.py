import os
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EmailSender:
    def __init__(self):
        self.gmail_service = self.setup_gmail_service()

    def setup_gmail_service(self):
        credentials = service_account.Credentials.from_service_account_file(
            settings.GMAIL_SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )
        service = build('gmail', 'v1', credentials=credentials)
        return service.users()

    def send_email(self, subject, to_email, html_content):
        message = EmailMultiAlternatives(subject, strip_tags(html_content), settings.DEFAULT_FROM_EMAIL, [to_email])
        message.attach_alternative(html_content, "text/html")
        message.send(fail_silently=False)
        return True
