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
        start_date = today.replace(year=today.year - 1, month=8, day=23)
        end_date = today.replace(year=today.year - 1, month=9, day=23)

        customers = Post.objects.filter(created__range=[start_date, end_date])

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

            for customer in customers:
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

        except Exception as e:
            self.stderr.write(f'An error occurred: {e}')

