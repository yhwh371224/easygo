import logging
from datetime import date, timedelta
from itertools import zip_longest

from django.core.management.base import BaseCommand
from blog.models import Post
from utils import booking_helper
from utils.booking_helper import assign_default_driver, build_reminder_context
from utils.email import send_template_email, collect_recipients
from basecamp.modules.date_utils import format_pickup_time_12h

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send booking reminder emails for upcoming flights'

    def handle(self, *args, **options):
        # --- 오늘 국제선 도착 예약 meeting_point 업데이트 ---
        booking_helper.update_meeting_point_for_arrivals()

        reminder_intervals = [0, 1, 3, 5, 7, 14, 28, -1]
        templates = [
            "html_email-today.html",
            "html_email-tomorrow.html",
            "html_email-upcoming3.html",
            "html_email-upcoming5.html",
            "html_email-upcoming7.html",
            "html_email-upcoming14.html",
            "html_email-upcoming28.html",
            "html_email-yesterday.html",
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
            driver = assign_default_driver(booking_reminder)
            pickup_time_12h = format_pickup_time_12h(booking_reminder.pickup_time)
            context = build_reminder_context(booking_reminder, pickup_time_12h, driver)
            # 당일(Reminder-Today)은 email만, 나머지는 booker_email도 추가
            if subject == "Reminder-Today":
                email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1)
            else:
                email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1, booking_reminder.booker_email)

            try:
                send_template_email(subject, template_name, context, email_recipients, fail_silently=False)
                logger.info(
                    f"Successfully sent '{subject}' email to {email_recipients} for pickup on {target_date}"
                )
            except Exception as e:
                logger.error(f"Failed to send email to {email_recipients}: {str(e)}")
