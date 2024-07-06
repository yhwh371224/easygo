import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger('blog.no_payment_yet')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(message)s')

# Create the logs directory if it doesn't exist
logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'no_payment_yet.log'))
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

class Command(BaseCommand):
    help = 'Send reminders for payment'

    def send_email(self, subject, template, context, recipient_list):
        html_content = render_to_string(template, context)
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(subject, text_content, '', recipient_list)
        email.attach_alternative(html_content, "text/html")
        try:
            email.send(fail_silently=False)
            logger.info(f"Email sent to {recipient_list}")
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_list}: {e}")

    def handle(self, *args, **options):
        dates_to_check = {
            "three_days": date.today() + timedelta(days=3),
            "tomorrow": date.today() + timedelta(days=1),
            "today": date.today(),
        }

        for key, check_date in dates_to_check.items():
            bookings = Post.objects.filter(pickup_date=check_date, cancelled=False, paid=False, cash=False)
            
            for booking in bookings:
                if key == "today":
                    subject = "Urgent notice for payment"
                    template = "basecamp/html_email-nopayment-today.html"
                    
                else:  # "three_days" or "tomorrow"
                    subject = "Payment notice"
                    template = "basecamp/html_email-nopayment.html"

                self.send_email(
                                subject,
                                template,
                                {'name': booking.name, 'email': booking.email},
                                [booking.email, RECIPIENT_EMAIL]
                            )

