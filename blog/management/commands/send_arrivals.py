import logging
from datetime import date, datetime
import pytz

from django.core.management.base import BaseCommand
from blog.models import Post

from utils import booking_helper
from utils.booking_helper import assign_default_driver, build_reminder_context
from utils.email import send_template_email, collect_recipients
from basecamp.modules.date_utils import format_pickup_time_12h
from blog.sms_utils import normalize_phone

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from decouple import config

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send reminders ONLY for today's arrivals (intl/domestic/all)"

    # =========================
    # INIT
    # =========================
    def handle(self, *args, **options):
        booking_helper.update_meeting_point_for_arrivals()

        self.account_sid = config('TWILIO_ACCOUNT_SID')
        self.auth_token = config('TWILIO_AUTH_TOKEN')
        self.messaging_service_sid = config('TWILIO_MESSAGING_SERVICE_SID')
        self.twilio_whatsapp_from = config('TWILIO_WHATSAPP_FROM')

        self.twilio_client = Client(self.account_sid, self.auth_token)

        self.send_today_arrivals(options['arrivals'])

    # =========================
    # MAIN FLOW
    # =========================
    def send_today_arrivals(self, arrival_type="all"):
        target_date = date.today()
        sydney_tz = pytz.timezone("Australia/Sydney")
        now_dt = datetime.now(sydney_tz)

        queryset = Post.objects.filter(
            pickup_date=target_date,
            direction__icontains="Pickup from"
        ).exclude(cancelled=True).select_related('driver')

        if arrival_type == "intl":
            queryset = queryset.filter(direction="Pickup from Intl Airport")
        elif arrival_type == "domestic":
            queryset = queryset.filter(direction="Pickup from Domestic Airport")

        booking_list = []

        for b in queryset:
            if b.pickup_time:
                try:
                    pickup_time_obj = datetime.strptime(b.pickup_time, "%H:%M").time()
                    pickup_dt = datetime.combine(target_date, pickup_time_obj)

                    if pickup_dt >= now_dt.replace(tzinfo=None):
                        booking_list.append(b)

                except ValueError:
                    booking_list.append(b)
            else:
                booking_list.append(b)

        if not booking_list:
            msg = f"No {arrival_type} arrivals for today."
            logger.info(msg)
            self.stdout.write(msg)
            return

        template_name = "html_email-today.html"
        subject = f"Reminder - Today ({arrival_type.capitalize()} Arrivals)"

        self.send_email_task(booking_list, template_name, subject)

        self.stdout.write(f"Total reminders processed: {len(booking_list)}")

    # =========================
    # SMS (EasyGo Messaging Service)
    # =========================
    def send_sms_reminder(self, sendto, name, pickup_date, email, price):
        formatted_number = normalize_phone(sendto)

        if not formatted_number:
            logger.warning(f"[SMS] Invalid number for {name}")
            return False

        message_body = self.build_message(name, pickup_date)

        try:
            self.twilio_client.messages.create(
                body=message_body,
                messaging_service_sid=self.messaging_service_sid,
                to=formatted_number
            )

            logger.info(f"[SMS SENT] {name} {formatted_number}")
            return True

        except TwilioRestException as e:
            logger.error(
                f"[SMS ERROR] {name} {formatted_number} "
                f"code={e.code} msg={e.msg}"
            )
            return False

    # =========================
    # WhatsApp fallback
    # =========================
    def send_whatsapp_reminder(self, sendto, name, pickup_date, email, price):
        formatted_number = normalize_phone(sendto)

        if not formatted_number:
            logger.warning(f"[WA] Invalid number for {name}")
            return

        message_body = self.build_message(name, pickup_date)

        try:
            self.twilio_client.messages.create(
                body=message_body,
                from_=f'whatsapp:{self.twilio_whatsapp_from}',
                to=f'whatsapp:{formatted_number}'
            )

            logger.info(f"[WA SENT] {name} {formatted_number}")

        except TwilioRestException as e:
            logger.error(
                f"[WA ERROR] {name} {formatted_number} "
                f"code={e.code} msg={e.msg}"
            )

    # =========================
    # EMAIL + NOTIFICATION FLOW
    # =========================
    def send_email_task(self, booking_reminders, template_name, subject):
        for booking in booking_reminders:

            # future-safe hook (optional DB field)
            if getattr(booking, "notification_sent", False):
                continue

            driver = assign_default_driver(booking)
            pickup_time_12h = format_pickup_time_12h(booking.pickup_time)

            context = build_reminder_context(
                booking,
                pickup_time_12h,
                driver
            )

            recipients = collect_recipients(
                booking.email,
                booking.email1
            )

            # EMAIL
            try:
                send_template_email(
                    subject,
                    template_name,
                    context,
                    recipients,
                    fail_silently=False
                )
                logger.info(f"[EMAIL SENT] {booking.email}")

            except Exception as e:
                logger.error(f"[EMAIL ERROR] {booking.email} {str(e)}")

            # SMS
            sms_sent = False

            if booking.sms_reminder and (booking.paid or booking.cash):
                sms_sent = self.send_sms_reminder(
                    booking.contact,
                    booking.name,
                    booking.pickup_date,
                    booking.email,
                    booking.price
                )

            # WhatsApp fallback (intl only)
            if (
                not sms_sent
                and booking.sms_reminder
                and (booking.paid or booking.cash)
                and booking.direction == "Pickup from Intl Airport"
            ):
                logger.warning(f"SMS failed → WhatsApp fallback {booking.name}")

                self.send_whatsapp_reminder(
                    booking.contact,
                    booking.name,
                    booking.pickup_date,
                    booking.email,
                    booking.price
                )

    # =========================
    # MESSAGE BUILDER
    # =========================
    def build_message(self, name, pickup_date):
        return (
            f"Hi {name}, your EasyGo booking is on {pickup_date}. "
            f"Please check your email for details."
        )