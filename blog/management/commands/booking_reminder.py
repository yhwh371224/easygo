import logging
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from datetime import date, timedelta
from main.settings import RECIPIENT_EMAIL


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send booking reminders for upcoming flights'

    def handle(self, *args, **options):
        self.send_email_1()
        self.send_email_2()
        self.send_email_3()
        self.send_email_4()
        self.send_email_5()
        self.send_email_6()

    def send_email_1(self):
        tomorrow_reminder = date.today() + timedelta(days=1)
        tomorrow_reminders = Post.objects.filter(flight_date=tomorrow_reminder)
        self.send_email_task(tomorrow_reminders, "basecamp/html_email-tomorrow.html", "Reminder - tomorrow")

    def send_email_2(self):
        upcoming3_reminder = date.today() + timedelta(days=3)
        upcoming3_reminders = Post.objects.filter(flight_date=upcoming3_reminder)
        self.send_email_task(upcoming3_reminders, "basecamp/html_email-upcoming3.html", "Reminder - 3days")

    def send_email_3(self):
        upcoming7_reminder = date.today() + timedelta(days=7)
        upcoming7_reminders = Post.objects.filter(flight_date=upcoming7_reminder)
        self.send_email_task(upcoming7_reminders, "basecamp/html_email-upcoming7.html", "Reminder - 7days")

    def send_email_4(self):
        upcoming14_reminder = date.today() + timedelta(days=14)
        upcoming14_reminders = Post.objects.filter(flight_date=upcoming14_reminder)
        self.send_email_task(upcoming14_reminders, "basecamp/html_email-upcoming14.html", "Reminder - 2wks")

    def send_email_5(self):
        today_reminder = date.today()
        today_reminders = Post.objects.filter(flight_date=today_reminder)
        self.send_email_task(today_reminders, "basecamp/html_email-today.html", "Notice - EasyGo")

    def send_email_6(self):
        yesterday_reminder = date.today() + timedelta(days=-1)
        yesterday_reminders = Post.objects.filter(flight_date=yesterday_reminder)
        self.send_email_task(yesterday_reminders, "basecamp/html_email-yesterday.html", "Review - EasyGo")

    def send_email_task(self, reminders, template_name, subject):
        emails_sent = 0  # Initialize the counter
        for reminder in reminders:
            if reminder.cancelled:
                continue
            elif reminder.flight_date:
                driver_instance = reminder.driver            
             
                driver_name = driver_instance.driver_name
                driver_contact = driver_instance.driver_contact
                driver_plate = driver_instance.driver_plate
                driver_car = driver_instance.driver_car

                html_content = render_to_string(template_name, {
                    'name': reminder.name, 'flight_date': reminder.flight_date, 'flight_number': reminder.flight_number,
                    'flight_time': reminder.flight_time, 'direction': reminder.direction, 'pickup_time': reminder.pickup_time,
                    'street': reminder.street, 'suburb': reminder.suburb, 'price': reminder.price, 'meeting_point': reminder.meeting_point,
                    'driver_name': driver_name, 'driver_contact': driver_contact, 'driver_plate': driver_plate, 'driver_car': driver_car
                })
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives(subject, text_content, '', [reminder.email])
                email.attach_alternative(html_content, "text/html")
                email.send()

                # Log information about each email sent
                logger.info(f"Email sent to {reminder.email} for booking reminder.")

        logger.info(f"Total {emails_sent} emails sent for booking reminder.")
        self.stdout.write(self.style.SUCCESS(f"{emails_sent} emails sent."))
