import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from blog.models import Post
from utils.email_helper import EmailSender
from main.settings import RECIPIENT_EMAIL

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Command(BaseCommand):
    help = 'Send payment notices'

    def handle(self, *args, **options):
        email_sender = EmailSender()

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

                html_content = render_to_string(template, {'name': booking.name, 'email': booking.email})
                try:
                    email_sender.send_email(subject, [booking.email, RECIPIENT_EMAIL], html_content)
                    self.stdout.write(self.style.SUCCESS(f"Payment notice email sent to {booking.email}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send email to {booking.email}: {e}"))
