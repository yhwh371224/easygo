from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from blog.models import Post  

from google.oauth2 import service_account
from googleapiclient.discovery import build
from email.message import EmailMessage
import base64


class Command(BaseCommand):
    help = 'Send good news to customers'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        start_date = timezone.datetime(2023, 2, 9).date()
        end_date = timezone.datetime(2023, 7, 7).date()

        # Filter customers where Pickup_date is missing
        customers = Post.objects.filter(
            created__range=[start_date, end_date],
            cancelled=False, 
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

            subject = 'Exciting News from EasyGo Airport Shuttle!'
            message_body = (
                "Dear Valued Customer,\n\n"
                "We are excited to share some wonderful news with you! EasyGo Airport Shuttle has been awarded the 2024 Quality Business Award by the Inner West Council. "
                "This recognition is a testament to our commitment to providing excellent service to all our customers.\n\n"
                "We want to express our sincere gratitude for your continued support, which has been instrumental in achieving this honor.\n\n"
                "For more details about this award and what it means for EasyGo Airport Shuttle, please click the link below:\n"
                "https://qualitybusinessawards.com.au/2024/the-best-airport-shuttle-service-in-inner-west-council/easygo-airport-shuttle\n\n"
                "Thank you for choosing EasyGo Airport Shuttle. We look forward to serving you again soon.\n\n"
                "Best regards,\n\n"
                "The EasyGo Airport Shuttle Team\n"
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

