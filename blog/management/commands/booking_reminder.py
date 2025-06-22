import os
import logging
from datetime import datetime, date, timedelta

from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from blog.models import Post, Driver

from twilio.rest import Client
from decouple import config
from itertools import zip_longest

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Command(BaseCommand):
    help = 'Send booking reminders for upcoming flights'

    def handle(self, *args, **options):
        # Initialize Twilio client once
        account_sid = config('TWILIO_ACCOUNT_SID')
        auth_token = config('TWILIO_AUTH_TOKEN')
        self.twilio_from = config('TWILIO_SMS_FROM')
        self.twilio_whatsapp_from = config('TWILIO_WHATSAPP_FROM')
        self.twilio_client = Client(account_sid, auth_token)

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
            sms_allowed = interval in [1, 3]
            self.send_email(interval, template, subject, sms_allowed)

    def format_pickup_time_12h(self, pickup_time_str):
        try:
            time_obj = datetime.strptime(pickup_time_str.strip(), "%H:%M")
            return time_obj.strftime("%I:%M %p")  
        except (ValueError, AttributeError):
            return pickup_time_str
        
    def format_phone_number(self, phone_number):
        if not phone_number:
            return None
        phone_number = phone_number.strip()
        if phone_number.startswith('+'):
            return phone_number
        elif phone_number.startswith('0'):
            return '+61' + phone_number[1:]
        else:
            return '+' + phone_number

    def send_sms_reminder(self, sendto, name, pickup_date, email, price):
        formatted_number = self.format_phone_number(sendto)
        if not formatted_number:
            logger.warning(f"Invalid phone number for {name}, skipping SMS.")
            return

        message_body = f"""
        Hi {name}, this is a reminder for your EasyGo booking on {pickup_date}.
        Please check your email for details. Reply by email.
        """.strip()
        try:
            self.twilio_client.messages.create(
                body=message_body,
                from_=self.twilio_from,
                to=formatted_number
            )
            logger.info(f"SMS sent to {name} ({formatted_number}) | Email: {email} | Price: ${price}")
        except Exception as e:
            logger.error(f"Failed to send SMS to {name} ({formatted_number}) | Email: {email} | Price: ${price} | Error: {str(e)}") 

    def send_whatsapp_reminder(self, sendto, name, pickup_date, email, price):
        formatted_number = self.format_phone_number(sendto)
        if not formatted_number:
            logger.warning(f"Invalid phone number for WhatsApp ({name}, {email}), skipping.")
            return

        message_body = f"""
        Hi {name}, this is a reminder for your EasyGo booking on {pickup_date}.
        Please check your email for details. Reply by email.
        """.strip()

        try:
            self.twilio_client.messages.create(
                body=message_body,
                from_=self.twilio_whatsapp_from,
                to=f'whatsapp:{formatted_number}'
            )
            logger.info(f"WhatsApp sent to {name} ({formatted_number}) | Email: {email} | Price: ${price}")
        except Exception as e:
            logger.error(f"Failed to send WhatsApp to {name} ({formatted_number}) | Email: {email} | Price: ${price} | Error: {str(e)}")

    def send_email(self, date_offset, template_name, subject, sms_allowed):
        target_date = date.today() + timedelta(days=date_offset)
        booking_reminders = Post.objects.filter(pickup_date=target_date).exclude(cancelled=True).select_related('driver')
        self.send_email_task(booking_reminders, template_name, subject, target_date, sms_allowed)

    def send_email_task(self, booking_reminders, template_name, subject, target_date, sms_allowed):
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
                'driver_name': driver.driver_name,
                'driver_contact': driver.driver_contact,
                'driver_plate': driver.driver_plate,
                'driver_car': driver.driver_car,
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
                logger.error(f"Failed to send email to {booking_reminder.email}: {str(e)}")

            # 📱 Send SMS if applicable
            if booking_reminder.sms_reminder is True and booking_reminder.contact and sms_allowed:
                self.send_sms_reminder(
                    booking_reminder.contact,
                    booking_reminder.name,
                    booking_reminder.pickup_date,
                    booking_reminder.email,
                    booking_reminder.price
                )
                self.send_whatsapp_reminder(
                    booking_reminder.contact,
                    booking_reminder.name,
                    booking_reminder.pickup_date,
                    booking_reminder.email,
                    booking_reminder.price
                )

            conditions = [
                (not booking_reminder.calendar_event_id, "calendar empty id - from booking_reminder"),
                (booking_reminder.toll == 'short payment', "short payment - from booking_reminder"),
            ]

            for condition, email_subject in conditions:
                if condition and booking_reminder.email:
                    try:
                        diff = round(float(booking_reminder.price or 0) - float(booking_reminder.paid or 0), 2)
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