import logging
import os
from datetime import date, timedelta

from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from blog.models import Post


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class EmailSender:
    def __init__(self):
        self.logger = self.setup_logger()
        self.gmail_service = self.setup_gmail_service()

    def setup_logger(self):
        logger = logging.getLogger('email.sender')
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s:%(message)s')
        logs_dir = os.path.join(BASE_DIR, 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        file_handler = logging.FileHandler(os.path.join(logs_dir, 'email_sender.log'))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def setup_gmail_service(self):
        credentials = service_account.Credentials.from_service_account_file(
            settings.GMAIL_API_SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )
        service = build('gmail', 'v1', credentials=credentials)
        return service.users()

    def send_email(self, subject, to_email, html_content):
        message = EmailMultiAlternatives(subject, strip_tags(html_content), settings.DEFAULT_FROM_EMAIL, [to_email])
        message.attach_alternative(html_content, "text/html")
        try:
            message.send(fail_silently=False)
            self.logger.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email}: {e}")
            return False
