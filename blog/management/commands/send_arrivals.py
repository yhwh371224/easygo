import logging
from datetime import date, datetime, time
import pytz

from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from blog.models import Post, Driver
from utils import booking_helper

from twilio.rest import Client
from decouple import config

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send reminders ONLY for today\'s arrivals (intl/domestic/all)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--arrivals',
            choices=['intl', 'domestic', 'all'],
            required=True,
            help='Send today\'s arrivals reminders (intl/domestic/all)'
        )

    def handle(self, *args, **options):
        booking_helper.update_meeting_point_for_arrivals()

        # Twilio init
        account_sid = config('TWILIO_ACCOUNT_SID')
        auth_token = config('TWILIO_AUTH_TOKEN')
        self.twilio_from = config('TWILIO_SMS_FROM')
        self.twilio_whatsapp_from = config('TWILIO_WHATSAPP_FROM')
        self.twilio_client = Client(account_sid, auth_token)

        # 실행
        self.send_today_arrivals(options['arrivals'])

    def send_today_arrivals(self, arrival_type="all"):
        target_date = date.today()
        sydney_tz = pytz.timezone("Australia/Sydney")
        now_time = datetime.now(sydney_tz).time()

        queryset = Post.objects.filter(
            pickup_date=target_date,
            direction__icontains="Pickup from"
        ).exclude(cancelled=True).select_related('driver')

        # 타입 필터
        if arrival_type == "intl":
            queryset = queryset.filter(direction="Pickup from Intl Airport")
        elif arrival_type == "domestic":
            queryset = queryset.filter(direction="Pickup from Domestic Airport")

        # 현재 시간 이전 예약 제외 (문자열 -> time)
        booking_list = []
        for b in queryset:
            if b.pickup_time:
                try:
                    pickup_time_obj = datetime.strptime(b.pickup_time, "%H:%M").time()
                    if pickup_time_obj >= now_time:
                        booking_list.append(b)
                except ValueError:
                    booking_list.append(b)  # 형식 오류 시 포함
            else:
                booking_list.append(b)  # 시간 없는 경우 포함

        if not booking_list:
            msg = f"No {arrival_type} arrivals for today (after current Sydney time)."
            logger.info(msg)
            self.stdout.write(msg)
            return

        template_name = "basecamp/html_email-today.html"
        subject = f"Reminder - Today ({arrival_type.capitalize()} Arrivals)"
        sms_allowed = True

        self.send_email_task(booking_list, template_name, subject, target_date, sms_allowed)

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
            msg = f"Invalid phone number for {name}, skipping SMS."
            logger.warning(msg)
            self.stdout.write(msg)
            return

        message_body = f"Hi {name}, your EasyGo booking is on {pickup_date}. Please check your email for details."
        try:
            self.twilio_client.messages.create(
                body=message_body,
                from_=self.twilio_from,
                to=formatted_number
            )
            msg = f"SMS sent to {name} ({formatted_number}) | Email: {email} | Price: ${price}"
            logger.info(msg)
            self.stdout.write(msg)
        except Exception as e:
            msg = f"Failed to send SMS to {name} ({formatted_number}) | Error: {str(e)}"
            logger.error(msg)
            self.stdout.write(msg)

    def send_whatsapp_reminder(self, sendto, name, pickup_date, email, price):
        formatted_number = self.format_phone_number(sendto)
        if not formatted_number:
            msg = f"Invalid phone number for WhatsApp ({name}, {email}), skipping."
            logger.warning(msg)
            self.stdout.write(msg)
            return

        message_body = f"Hi {name}, your EasyGo booking is on {pickup_date}. Please check your email for details."
        try:
            self.twilio_client.messages.create(
                body=message_body,
                from_=self.twilio_whatsapp_from,
                to=f'whatsapp:{formatted_number}'
            )
            msg = f"WhatsApp sent to {name} ({formatted_number}) | Email: {email} | Price: ${price}"
            logger.info(msg)
            self.stdout.write(msg)
        except Exception as e:
            msg = f"Failed to send WhatsApp to {name} ({formatted_number}) | Error: {str(e)}"
            logger.error(msg)
            self.stdout.write(msg)

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
                'meeting_point': booking_reminder.meeting_point,
                'driver_name': driver.driver_name,
                'driver_contact': driver.driver_contact,
                'driver_plate': driver.driver_plate,
                'driver_car': driver.driver_car,
                'paid': booking_reminder.paid,
                'cash': booking_reminder.cash,
            })

            text_content = strip_tags(html_content)
            email_recipients = [booking_reminder.email]
            if booking_reminder.email1 and booking_reminder.email1.strip():
                email_recipients.append(booking_reminder.email1.strip())

            email = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, email_recipients)
            email.attach_alternative(html_content, "text/html")

            try:
                email.send(fail_silently=False)
                msg = f"Sent '{subject}' email to {booking_reminder.email}"
                logger.info(msg)
                self.stdout.write(msg)
            except Exception as e:
                msg = f"Failed to send email to {booking_reminder.email}: {str(e)}"
                logger.error(msg)
                self.stdout.write(msg)

            # SMS
            if booking_reminder.sms_reminder and (booking_reminder.paid or booking_reminder.cash):
                self.send_sms_reminder(
                    booking_reminder.contact,
                    booking_reminder.name,
                    booking_reminder.pickup_date,
                    booking_reminder.email,
                    booking_reminder.price
                )

            # WhatsApp (국제선 도착만)
            if (booking_reminder.sms_reminder
                and (booking_reminder.paid or booking_reminder.cash)
                and booking_reminder.direction == "Pickup from Intl Airport"):
                self.send_whatsapp_reminder(
                    booking_reminder.contact,
                    booking_reminder.name,
                    booking_reminder.pickup_date,
                    booking_reminder.email,
                    booking_reminder.price
                )

        self.stdout.write(f"Total reminders processed: {len(booking_reminders)}")
