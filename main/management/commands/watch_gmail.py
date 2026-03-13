from django.core.management.base import BaseCommand
from googleapiclient.discovery import build
from google.oauth2 import service_account
from django.conf import settings 


class Command(BaseCommand):
    help = 'Start Gmail Watch for INBOX'

    def handle(self, *args, **options):
        SCOPES = ['https://mail.google.com/']
        SERVICE_ACCOUNT_FILE = settings.GMAIL_SERVICE_ACCOUNT_FILE
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        delegated_creds = creds.with_subject("info@easygoshuttle.com.au")

        try:        
            service = build('gmail', 'v1', credentials=delegated_creds)
            response = service.users().watch(
                userId='me',
                body={
                    'labelIds': ['INBOX'],
                    'topicName': 'projects/gmail-watch-490101/topics/gmail-watch-topic'
                }
            ).execute()

            self.stdout.write(self.style.SUCCESS(
                f"Gmail Watch started\nHistoryId: {response.get('historyId')}\nExpiration: {response.get('expiration')}"
            ))

        except Exception as e:
            self.stderr.write(f'An error occurred: {e}')