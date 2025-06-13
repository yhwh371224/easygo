import os
import logging
from datetime import datetime, date, timedelta

from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from blog.models import Post
from itertools import zip_longest

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Command(BaseCommand):
    help = 'Send booking reminders for upcoming flights'

    def handle(self, *args, **options):
        reminder_intervals = [0, 1, 3, 5, 7, 14, 28, -1]
        # reminder_intervals = [-1]
        templates = [
            "basecamp/html_email-today.html",
            "basecamp/html_email-tomorrow.html",
            "basecamp/html_email-upcoming3.html",
            "basecamp/html_email-upcoming5.html",
            "basecamp/html_email-upcoming7.html",
            "basecamp/html_email-upcoming14.html",
            "basecamp/html_email-upcoming28.html",
            "basecamp/html_email-yesterday.html",
        ]
        subjects = [
            "Reminder-Today",
            "Reminder-Tomorrow",
            "Reminder-3days",
            "Reminder-5days",
            "Reminder-7days",
            "Reminder-2wks",
            "Reminder-4wks",
            "Review-EasyGo",
        ]
        for interval, template, subject in zip_longest(reminder_intervals, templates, subjects, fillvalue=""):
            self.send_email(interval, template, subject)

    def format_pickup_time_12h(self, pickup_time_str):
        try:
            time_obj = datetime.strptime(pickup_time_str.strip(), "%H:%M")
            return time_obj.strftime("%I:%M %p")  # e.g., 06:30 PM
        except (ValueError, AttributeError):
            return pickup_time_str  # Return original if invalid format

    def send_email(self, date_offset, template_name, subject):
        target_date = date.today() + timedelta(days=date_offset)
        booking_reminders = Post.objects.filter(pickup_date=target_date).exclude(cancelled=True).select_related('driver')
        self.send_email_task(booking_reminders, template_name, subject, target_date)

    def send_email_task(self, booking_reminders, template_name, subject, target_date):
        for booking_reminder in booking_reminders:

            driver = booking_reminder.driver

            pickup_time_12h = self.format_pickup_time_12h(booking_reminder.pickup_time)

            html_content = render_to_string(template_name, {
                'name': booking_reminder.name,
                'company_name': booking_reminder.company_name,
                'email': booking_reminder.email,
                'email1': booking_reminder.email1,
                'pickup_date': booking_reminder.pickup_date,
                'flight_number': booking_reminder.flight_number,
                'flight_time': booking_reminder.flight_time,
                'direction': booking_reminder.direction,
                'pickup_time': pickup_time_12h,
                'start_point': booking_reminder.start_point or "",  
                'end_point': booking_reminder.end_point or "",    
                'street': booking_reminder.street,
                'suburb': booking_reminder.suburb,
                'price': booking_reminder.price,
                'reminder': booking_reminder.reminder,
                'meeting_point': booking_reminder.meeting_point,
                'driver_name': driver.driver_name if driver else "",
                'driver_contact': driver.driver_contact if driver else "",
                'driver_plate': driver.driver_plate if driver else "",
                'driver_car': driver.driver_car if driver else "",
                'paid': booking_reminder.paid,
                'cash': booking_reminder.cash,
                'cruise': booking_reminder.cruise,
            })

            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [booking_reminder.email, booking_reminder.email1])
            email.attach_alternative(html_content, "text/html")

            try:
                email.send(fail_silently=False)
                logger.info(f"Successfully sent '{subject}' email to {booking_reminder.email} for pickup on {target_date}")
            except Exception as e:
                logging.error(f"Failed to send email to {booking_reminder.email}: {str(e)}")

            booking_reminder.save()

            conditions = [
                (not booking_reminder.calendar_event_id, "calendar empty id - from booking_reminder"),
                (booking_reminder.toll == 'short payment', "short payment - from booking_reminder"),
            ]

            for condition, email_subject in conditions:
                if condition and booking_reminder.email:
                    try:
                        diff = round(float(booking_reminder.price) - float(booking_reminder.paid), 2)
                        html_content = render_to_string(
                            "basecamp/html_email-shortpayment-alert.html",  
                            {
                                'name': booking_reminder.name,
                                'email': booking_reminder.email,
                                'note': email_subject,
                                'pickup_date': booking_reminder.pickup_date,
                                'price': booking_reminder.price,
                                'paid': booking_reminder.paid,
                                'diff': diff,
                            }
                        )
                        text_content = strip_tags(html_content)

                        email = EmailMultiAlternatives(
                            email_subject,
                            text_content,
                            settings.DEFAULT_FROM_EMAIL,
                            [booking_reminder.email, settings.DEFAULT_FROM_EMAIL]
                        )
                        email.attach_alternative(html_content, "text/html")
                        email.send()
                        logger.info(f"Sent HTML alert '{email_subject}' to customer: {booking_reminder.email}")
                    except Exception as e:
                        logger.error(f"Failed to send HTML alert to customer {booking_reminder.email}: {str(e)}")