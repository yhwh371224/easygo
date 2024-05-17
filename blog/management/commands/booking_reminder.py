import os 
import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from main.settings import RECIPIENT_EMAIL

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger('blog.booking_reminders')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(message)s')

# Create the logs directory if it doesn't exist
logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'booking_reminders.log'))
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

class Command(BaseCommand):
    help = 'Send booking reminders for upcoming flights'

    def handle(self, *args, **options):
        self.send_email(0, "basecamp/html_email-today.html", "Reminder-Today")
        self.send_email(1, "basecamp/html_email-tomorrow.html", "Reminder-tomorrow")
        self.send_email(3, "basecamp/html_email-upcoming3.html", "Reminder-3days")
        self.send_email(7, "basecamp/html_email-upcoming7.html", "Reminder-7days")
        self.send_email(14, "basecamp/html_email-upcoming14.html", "Reminder-2wks")        
        self.send_email(-1, "basecamp/html_email-yesterday.html", "Review-EasyGo")

    def send_email(self, date_offset, template_name, subject):
        target_date = date.today() + timedelta(days=date_offset)
        booking_reminders = Post.objects.filter(flight_date=target_date, cancelled=False)
        self.send_email_task(booking_reminders, template_name, subject)

    def send_email_task(self, booking_reminders, template_name, subject):
                
        for booking_reminder in booking_reminders:
            driver_instance = booking_reminder.driver
            driver_name, driver_contact, driver_plate, driver_car = "", "", "", ""   

            if driver_instance:
                driver_name = driver_instance.driver_name
                driver_contact = driver_instance.driver_contact
                driver_plate = driver_instance.driver_plate
                driver_car = driver_instance.driver_car

            html_content = render_to_string(template_name, {
                'name': booking_reminder.name, 'flight_date': booking_reminder.flight_date, 'flight_number': booking_reminder.flight_number,
                'flight_time': booking_reminder.flight_time, 'direction': booking_reminder.direction, 'pickup_time': booking_reminder.pickup_time,
                'street': booking_reminder.street, 'suburb': booking_reminder.suburb, 'price': booking_reminder.price, 'meeting_point': booking_reminder.meeting_point,
                'driver_name': driver_name, 'driver_contact': driver_contact, 'driver_plate': driver_plate, 'driver_car': driver_car, 
                'paid': booking_reminder.paid, 'cash': booking_reminder.cash
            })

            text_content = strip_tags(html_content)            
            email = EmailMultiAlternatives(subject, text_content, '', [booking_reminder.email])
            email.attach_alternative(html_content, "text/html")

            try:
                email.send()
                booking_reminder.save()
                logger.info(f"Email sent to {booking_reminder.email} for {booking_reminder.name}")
            except Exception as e:
                logger.error(f"Failed to send email to {booking_reminder.email} | {booking_reminder.flight_date} & {booking_reminder.pickup_time}: {e}")

            if not booking_reminder.calendar_event_id:
                confirmation_subject = "No confirmation yet - empty id"
                confirmation_message = f"{booking_reminder.name} & {booking_reminder.email}"
                recipient = [RECIPIENT_EMAIL]

                try:
                    send_mail(confirmation_subject, confirmation_message, '', recipient)
                    logger.info(f"No calendar event id: {booking_reminder.email} & {booking_reminder.name}")
                except Exception as e:
                    logger.error(f"Failed to send email to {booking_reminder.email} | {booking_reminder.flight_date} & {booking_reminder.pickup_time}: {e}")
