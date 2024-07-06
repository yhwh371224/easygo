from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from blog.models import Post  

from google.oauth2 import service_account
from googleapiclient.discovery import build
from email.message import EmailMessage
import base64


class Command(BaseCommand):
    help = 'Send apology emails to customers created in the last three months'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        start_date = timezone.datetime(2023, 2, 9).date()
        end_date = timezone.datetime(2023, 4, 5).date()

        # Filter customers where Pickup_date is missing
        customers = Post.objects.filter(
            created__range=[start_date, end_date],
            # Pickup_date__isnull=True
        )

        SCOPES = ['https://mail.google.com/']
        creds = service_account.Credentials.from_service_account_file(
            'secure/reminder/service-account-file.json', scopes=SCOPES
        )
        delegated_creds = creds.with_subject("info@easygoshuttle.com.au")

        try:
            # Call the Gmail API
            service = build('gmail', 'v1', credentials=delegated_creds)

            subject = 'Apology for Recent Email Error'
            message_body = (
                "Dear Valued Customer,\n\n"
                "I hope this email finds you well.\n\n"
                "We sincerely apologize for any inconvenience caused by a recent system issue that resulted in data loss, specifically booking dates (pickup dates). "
                "We have diligently worked to manually recover all the lost information and I am pleased to confirm that we have restored all booking details\n\n"
                "However, to ensure no errors occur, we kindly request your assistance."
                "If you do not receive a reminder email three days prior to your booking date, please contact us immediately to confirm your booking details. \n\n"                
                "We deeply regret any inconvenience this may cause and appreciate your understanding"
                "We are taking these steps to ensure no mistakes are made and to provide you with the best service possible.\n\n"
                "Thank you for your understanding and patience.\n\n"
                "Best regards,\n\n"
                "Peter\n"
                "EasyGo Airport Shuttle\n"
            )

            sent_emails = set()  

            for customer in customers:
                if customer.email in sent_emails:
                    continue  # Skip sending email if already sent

                message = EmailMessage()
                message.set_content(message_body)
                message['To'] = customer.email
                message['From'] = 'info@easygoshuttle.com.au'
                message['Subject'] = subject

                encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

                create_message = {
                    'raw': encoded_message
                }

                email = service.users().messages().send(userId="me", body=create_message).execute()
                self.stdout.write(self.style.SUCCESS(f'Email sent to {customer.email}'))

                sent_emails.add(customer.email)  # Add the email to sent_emails set

        except Exception as e:
            self.stderr.write(f'An error occurred: {e}')

