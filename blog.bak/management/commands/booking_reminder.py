import os
import logging
from datetime import datetime, date, timedelta
from itertools import zip_longest

from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from blog.models import Post, Driver
from utils import booking_helper

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'Send booking reminder emails for upcoming flights'

    def handle(self, *args, **options):
        # --- 오늘 국제선 도착 예약 meeting_point 업데이트 ---
        booking_helper.update_meeting_point_for_arrivals()

        reminder_intervals = [0, 1, 3, 5, 7, 14, 28, -1]
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
            return time_obj.strftime("%I:%M %p")
        except (ValueError, AttributeError):
            return pickup_time_str

    def send_email(self, date_offset, template_name, subject):
        target_date = date.today() + timedelta(days=date_offset)
        booking_reminders = (
            Post.objects.filter(pickup_date=target_date)
            .exclude(cancelled=True)
            .exclude(pending=True)
            .select_related('driver')
        )
        self.send_email_task(booking_reminders, template_name, subject, target_date)

    def send_email_task(self, booking_reminders, template_name, subject, target_date):
        for booking_reminder in booking_reminders:
            if not booking_reminder.driver:
                sam_driver = Driver.objects.get(driver_name="Sam")
                booking_reminder.driver = sam_driver
                booking_reminder.save()

            driver = booking_reminder.driver
            pickup_time_12h = self.format_pickup_time_12h(booking_reminder.pickup_time)

            html_content = render_to_string(template_name, {
                'name': booking_reminder.name,
                'company_name': booking_reminder.company_name,
                'email': booking_reminder.email,
                'email1': booking_reminder.email1,
                'contact': booking_reminder.contact,
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
                'reminder': getattr(booking_reminder, 'reminder', False),
                'sms_reminder': getattr(booking_reminder, 'sms_reminder', False), 
                'meeting_point': booking_reminder.meeting_point,
                'driver_name': driver.driver_name,
                'driver_contact': driver.driver_contact,
                'driver_plate': driver.driver_plate,
                'driver_car': driver.driver_car,
                'paid': booking_reminder.paid,
                'cash': booking_reminder.cash,
                'cruise': booking_reminder.cruise,
            })

            text_content = strip_tags(html_content)

            
            # ---- 여기 수정됨: email, email1에서 여러 주소 split ----
            email_recipients = []

            if booking_reminder.email:
                email_recipients.extend(
                    [e.strip() for e in booking_reminder.email.split(",") if e.strip()]
                )

            if booking_reminder.email1:
                email_recipients.extend(
                    [e.strip() for e in booking_reminder.email1.split(",") if e.strip()]
                )

            # 중복 제거
            email_recipients = list(set(email_recipients))
            # ---------------------------------------------

            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                email_recipients
            )
            email.attach_alternative(html_content, "text/html")

            try:
                email.send(fail_silently=False)
                logger.info(
                    f"Successfully sent '{subject}' email to {email_recipients} for pickup on {target_date}"
                )
            except Exception as e:
                logger.error(f"Failed to send email to {email_recipients}: {str(e)}")
