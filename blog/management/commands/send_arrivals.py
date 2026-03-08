import logging
from datetime import date, datetime
import pytz

from django.core.management.base import BaseCommand
from blog.models import Post
from utils import booking_helper
from utils.booking_helper import assign_default_driver, build_reminder_context
from utils.email import send_template_email, collect_recipients
from basecamp.modules.date_utils import format_pickup_time_12h

from twilio.rest import Client
from decouple import config

logger = logging.getLogger(__name__)


### intl/domestic/all 오늘 도착 알림 전송 명령어 ###


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

        self.send_today_arrivals(options['arrivals'])

    def send_today_arrivals(self, arrival_type="all"):
        target_date = date.today()
        sydney_tz = pytz.timezone("Australia/Sydney")
        now_time = datetime.now(sydney_tz).time()

        queryset = Post.objects.filter(
            pickup_date=target_date,
            direction__icontains="Pickup from"
        ).exclude(cancelled=True).select_related('driver')

        if arrival_type == "intl":
            queryset = queryset.filter(direction="Pickup from Intl Airport")
        elif arrival_type == "domestic":
            queryset = queryset.filter(direction="Pickup from Domestic Airport")

        # 현재 시간 이전 예약 제외
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

        template_name = "html_email-today.html"
        subject = f"Reminder - Today ({arrival_type.capitalize()} Arrivals)"
        sms_allowed = True

        self.send_email_task(booking_list, template_name, subject, target_date, sms_allowed)

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
            return True
        except Exception as e:
            msg = f"Failed to send SMS to {name} ({formatted_number}) | Error: {str(e)}"
            logger.error(msg)
            self.stdout.write(msg)
            return False

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
            driver = assign_default_driver(booking_reminder)
            pickup_time_12h = format_pickup_time_12h(booking_reminder.pickup_time)
            context = build_reminder_context(booking_reminder, pickup_time_12h, driver)
            email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1)

            try:
                send_template_email(subject, template_name, context, email_recipients, fail_silently=False)
                msg = f"Sent '{subject}' email to {booking_reminder.email}"
                logger.info(msg)
                self.stdout.write(msg)
            except Exception as e:
                msg = f"Failed to send email to {booking_reminder.email}: {str(e)}"
                logger.error(msg)
                self.stdout.write(msg)

            # SMS
            sms_sent = False

            if (
                booking_reminder.sms_reminder
                and (booking_reminder.paid or booking_reminder.cash)
            ):
                sms_sent = self.send_sms_reminder(
                    booking_reminder.contact,
                    booking_reminder.name,
                    booking_reminder.pickup_date,
                    booking_reminder.email,
                    booking_reminder.price
                )

            # WhatsApp (SMS 실패 시, 국제선만)
            if (
                not sms_sent
                and booking_reminder.sms_reminder
                and (booking_reminder.paid or booking_reminder.cash)
                and booking_reminder.direction == "Pickup from Intl Airport"
            ):
                self.send_whatsapp_reminder(
                    booking_reminder.contact,
                    booking_reminder.name,
                    booking_reminder.pickup_date,
                    booking_reminder.email,
                    booking_reminder.price
                )

        self.stdout.write(f"Total reminders processed: {len(booking_reminders)}")
