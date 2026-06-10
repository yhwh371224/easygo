import logging
from datetime import timedelta
from itertools import zip_longest

from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from utils import booking_helper
from utils.booking_helper import build_reminder_context
from utils.email import send_template_email, collect_recipients
from basecamp.modules.date_utils import format_pickup_time_12h

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send booking reminder emails for upcoming flights'

    def add_arguments(self, parser):
        parser.add_argument(
            '--today',
            action='store_true',
            help='Send only today\'s reminder emails',
        )

    def handle(self, *args, **options):
        # --- 오늘 국제선 도착 예약 meeting_point 업데이트 ---
        booking_helper.update_meeting_point_for_arrivals()

        reminder_intervals = [0, 1, 2, 3, 7, -5]  # -5: 5일 전 픽업 완료 고객 리뷰 요청
        templates = [
            "html_email-today.html",
            "html_email-tomorrow.html",
            "html_email-arrival-2days.html",
            "html_email-upcoming3.html",
            "html_email-upcoming7.html",
            "html_email-yesterday.html",
        ]
        subjects = [
            "Reminder-Today",
            "Reminder-Tomorrow",
            "Reminder-Arrival-2days",
            "Reminder-3days",
            "Reminder-7days",
            "Review-EasyGo",
        ]

        if options['today']:
            self.send_email(0, "html_email-today.html", "Reminder-Today")
            return

        for interval, template, subject in zip_longest(reminder_intervals, templates, subjects, fillvalue=""):
            self.send_email(interval, template, subject)

    def send_email(self, date_offset, template_name, subject):
        target_date = timezone.localdate() + timedelta(days=date_offset)
        booking_reminders = (
            Post.objects.filter(pickup_date=target_date)
            .exclude(cancelled=True)
            .exclude(pending=True)
            .select_related('driver')
        )
        if subject == "Reminder-Arrival-2days":
            booking_reminders = booking_reminders.filter(direction__istartswith="pickup")
        self.send_email_task(booking_reminders, template_name, subject, target_date)

    def send_email_task(self, booking_reminders, template_name, subject, target_date):
        for booking_reminder in booking_reminders:
            try:
                logger.info(f"[{subject}] Processing booking id={booking_reminder.id} email={booking_reminder.email} booker_email={booking_reminder.booker_email}")

                if not booking_reminder.driver and subject == "Reminder-Today":
                    logger.warning(f"[{subject}] SKIP id={booking_reminder.id} — no driver")
                    continue

                logger.info(f"[{subject}] id={booking_reminder.id} terminal_pickup_point={booking_reminder.terminal_pickup_point}")

                driver = getattr(booking_reminder, "driver", None)
                pickup_time_12h = format_pickup_time_12h(booking_reminder.pickup_time)
                context = build_reminder_context(booking_reminder, pickup_time_12h, driver)

                booker_email = booking_reminder.booker_email
                is_today = subject == "Reminder-Today"
                is_tomorrow = subject == "Reminder-Tomorrow"
                is_arrival_2days = subject == "Reminder-Arrival-2days"
                is_upcoming3 = subject == "Reminder-3days"
                is_upcoming7 = subject == "Reminder-7days"
                is_review = subject == "Review-EasyGo"

                if is_review:
                    # 리뷰 요청: 실제 탑승자에게만 (booker 제외)
                    email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1)
                elif booker_email:
                    if is_today:
                        email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1)
                    elif is_tomorrow or is_arrival_2days:
                        email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1, booker_email)
                    else:
                        # 7days: booker_email만
                        email_recipients = collect_recipients(booker_email)
                else:
                    email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1)

                logger.info(f"[{subject}] id={booking_reminder.id} email_recipients={email_recipients}")

                if is_today:
                    if booking_reminder.terminal_pickup_point:
                        today_template = "emails/driver_details.html"
                    else:
                        today_template = "html_email-today.html"
                    template_name = today_template
                    logger.info(f"[{subject}] id={booking_reminder.id} template={template_name}")

                if not email_recipients:
                    logger.warning(f"[{subject}] SKIP id={booking_reminder.id} — no recipients (email={booking_reminder.email} email1={booking_reminder.email1} booker_email={booker_email})")
                    continue

                try:
                    send_template_email(subject, template_name, context, email_recipients, fail_silently=False)
                    logger.info(
                        f"Successfully sent '{subject}' email to {email_recipients} for pickup on {target_date}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send email to {email_recipients}: {str(e)}")

            except Exception as e:
                logger.exception(
                    f"FAILED booking_reminder.id={booking_reminder.id} error={str(e)}"
                )
                continue