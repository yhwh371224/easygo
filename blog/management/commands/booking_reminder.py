import os
import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from utils.email_helper import EmailSender
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from main.settings import RECIPIENT_EMAIL, GMAIL_API_SERVICE_ACCOUNT_FILE
from blog.models import Post


class Command(BaseCommand):
    help = 'Send booking reminders for upcoming flights'

    def handle(self, *args, **options):
        email_sender = EmailSender(service_account_file=GMAIL_API_SERVICE_ACCOUNT_FILE)

        reminder_intervals = [0, 1, 3, 7, 14, -1]
        templates = [
            "basecamp/html_email-today.html",
            "basecamp/html_email-tomorrow.html",
            "basecamp/html_email-upcoming3.html",
            "basecamp/html_email-upcoming7.html",
            "basecamp/html_email-upcoming14.html",
            "basecamp/html_email-yesterday.html",
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
            self.send_email(email_sender, interval, template, subject)

    def send_email(self, email_sender, date_offset, template_name, subject):
        target_date = date.today() + timedelta(days=date_offset)
        booking_reminders = Post.objects.filter(pickup_date=target_date, cancelled=False).select_related('driver')

        for booking_reminder in booking_reminders:
            if target_date == date.today() and booking_reminder.discount == "TBA":
                email_sender.logger.info(f"Skipping email for {booking_reminder.email} due to no payment of TBA")
                continue

            driver = booking_reminder.driver
            html_content = render_to_string(template_name, {
                'name': booking_reminder.name,
                'pickup_date': booking_reminder.pickup_date,
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

            if not email_sender.send_email(subject, booking_reminder.email, html_content):
                # Handle failure if needed
                pass

            if not booking_reminder.calendar_event_id:
                self.send_calendar_event_id_email(email_sender, booking_reminder)

            if booking_reminder.toll == 'short payment':
                self.send_short_payment_email(email_sender, booking_reminder)

    def send_calendar_event_id_email(self, email_sender, booking_reminder):
        subject = "calendar empty id - from booking_reminder"
        message = f"{booking_reminder.name} & {booking_reminder.email}"
        recipient = RECIPIENT_EMAIL
        if not email_sender.send_email(subject, recipient, message):
            email_sender.logger.error(f"Failed to send calendar event id email to {booking_reminder.email}")

    def send_short_payment_email(self, email_sender, booking_reminder):
        subject = "short payment - from booking_reminder"
        message = f"{booking_reminder.name} & {booking_reminder.email}"
        recipient = RECIPIENT_EMAIL
        if not email_sender.send_email(subject, recipient, message):
            email_sender.logger.error(f"Failed to send short payment email to {booking_reminder.email}")