import os
import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from django.conf import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'Send booking reminders for upcoming flights'

    def __init__(self):
        super().__init__()
        self.logger = self.setup_logger()

    def setup_logger(self):
        logger = logging.getLogger('blog.booking_reminders')
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s:%(message)s')

        logs_dir = os.path.join(BASE_DIR, 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        file_handler = logging.FileHandler(os.path.join(logs_dir, 'booking_reminders.log'))
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        return logger

    def handle(self, *args, **options):
        reminder_intervals = [0, 1, 3, 7, 14]
        templates = [
            "basecamp/html_email-today.html",
            "basecamp/html_email-tomorrow.html",
            "basecamp/html_email-upcoming3.html",
            "basecamp/html_email-upcoming7.html",
            "basecamp/html_email-upcoming14.html",
            # "basecamp/html_email-yesterday.html",
        ]
        subjects = [
            "Reminder-Today",
            "Reminder-Tomorrow",
            "Reminder-3days",
            "Reminder-7days",
            "Reminder-2wks",
            "Review-EasyGo",
        ]
        for interval, template, subject in zip(reminder_intervals, templates, subjects):
            self.send_email(interval, template, subject)

    def send_email(self, date_offset, template_name, subject):
        target_date = date.today() + timedelta(days=date_offset)
        booking_reminders = Post.objects.filter(flight_date=target_date, cancelled=False).select_related('driver')
        self.send_email_task(booking_reminders, template_name, subject, target_date)

    def send_email_task(self, booking_reminders, template_name, subject, target_date):
        for booking_reminder in booking_reminders:
            if target_date == date.today() and booking_reminder.discount == "TBA":
                self.logger.info(f"Skipping email for {booking_reminder.email} due to no payment of TBA")
                continue

            driver = booking_reminder.driver
            html_content = render_to_string(template_name, {
                'name': booking_reminder.name,
                'flight_date': booking_reminder.flight_date,
                'flight_number': booking_reminder.flight_number,
                'flight_time': booking_reminder.flight_time,
                'direction': booking_reminder.direction,
                'pickup_time': booking_reminder.pickup_time,
                'street': booking_reminder.street,
                'suburb': booking_reminder.suburb,
                'price': booking_reminder.price,
                'meeting_point': booking_reminder.meeting_point,
                'driver_name': driver.driver_name if driver else "",
                'driver_contact': driver.driver_contact if driver else "",
                'driver_plate': driver.driver_plate if driver else "",
                'driver_car': driver.driver_car if driver else "",
                'paid': booking_reminder.paid,
                'cash': booking_reminder.cash,
            })

            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [booking_reminder.email])
            email.attach_alternative(html_content, "text/html")

            try:
                email.send(fail_silently=False)
                booking_reminder.save()
                self.logger.info(f"Email sent to {booking_reminder.email} for {booking_reminder.name}")
            except Exception as e:
                self.logger.error(f"Failed to send email to {booking_reminder.email} | {booking_reminder.flight_date} & {booking_reminder.pickup_time}: {e}")

            if not booking_reminder.calendar_event_id:
                subject = "calendar empty id - from booking_reminder"
                message = f"{booking_reminder.name} & {booking_reminder.email}"
                recipient = [settings.RECIPIENT_EMAIL]

                try:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient, fail_silently=False)
                    self.logger.info(f"No calendar event id: {booking_reminder.email} & {booking_reminder.name}")
                except Exception as e:
                    self.logger.error(f"Failed to send calendar event id email to {booking_reminder.email} | {booking_reminder.flight_date} & {booking_reminder.pickup_time}: {e}")

