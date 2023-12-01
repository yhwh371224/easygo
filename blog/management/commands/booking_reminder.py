import os
import logging
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from datetime import date, timedelta
from main.settings import RECIPIENT_EMAIL


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger('blog.booking_reminder')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')

# Create the logs directory if it doesn't exist
logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'booking_reminder.log'))
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


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
        # pass 
        tomorrow_reminder = date.today() + timedelta(days=1)
        tomorrow_reminders = Post.objects.filter(flight_date=tomorrow_reminder)
        self.send_email_task(tomorrow_reminders, "basecamp/html_email-tomorrow.html", "Reminder-tomorrow")

    def send_email_2(self):
        # pass
        upcoming3_reminder = date.today() + timedelta(days=3)
        upcoming3_reminders = Post.objects.filter(flight_date=upcoming3_reminder)
        self.send_email_task(upcoming3_reminders, "basecamp/html_email-upcoming3.html", "Reminder-3days")

    def send_email_3(self):
        # pass
        upcoming7_reminder = date.today() + timedelta(days=7)
        upcoming7_reminders = Post.objects.filter(flight_date=upcoming7_reminder)
        self.send_email_task(upcoming7_reminders, "basecamp/html_email-upcoming7.html", "Reminder-7days")

    def send_email_4(self):
        # pass
        upcoming14_reminder = date.today() + timedelta(days=14)
        upcoming14_reminders = Post.objects.filter(flight_date=upcoming14_reminder)
        self.send_email_task(upcoming14_reminders, "basecamp/html_email-upcoming14.html", "Reminder-2wks")

    def send_email_5(self):
        # pass
        today_reminder = date.today()
        today_reminders = Post.objects.filter(flight_date=today_reminder)
        self.send_email_task(today_reminders, "basecamp/html_email-today.html", "Reminder-Today")

    def send_email_6(self):
        # pass
        yesterday_reminder = date.today() + timedelta(days=-1)
        yesterday_reminders = Post.objects.filter(flight_date=yesterday_reminder)
        self.send_email_task(yesterday_reminders, "basecamp/html_email-yesterday.html", "Review-EasyGo")

    def send_email_task(self, reminders, template_name, subject):
        emails_sent = 0  # Initialize the counter
        sent_emails_set = set()  # Set to track already sent emails

        try:
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

                    if reminder.email not in sent_emails_set:
                        # Add the sent email to the set only if it's not already in the set
                        sent_emails_set.add(reminder.email)              
                        emails_sent += 1

                    logger.info(f'{subject}: email sent to {reminder.name}')
            
        except Exception as e:            
            logger.exception(f"Error during booking reminders emailing: {e}")
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))
