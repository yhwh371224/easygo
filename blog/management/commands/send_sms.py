import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.conf import settings

from blog.models import Post
from blog.sms_utils import normalize_phone

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

sms_logger = logging.getLogger('sms')


class Command(BaseCommand):
    help = 'Send final notices via SMS or WhatsApp for unpaid future bookings'

    # =========================
    # INIT TWILIO CLIENT
    # =========================
    def init_twilio(self):
        return Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )

    # =========================
    # MAIN
    # =========================
    def handle(self, *args, **options):
        try:
            today = date.today()
            day_after_tomorrow = today + timedelta(days=3)

            client = self.init_twilio()

            messaging_service_sid = settings.TWILIO_MESSAGING_SERVICE_SID
            whatsapp_from = settings.TWILIO_WHATSAPP_FROM

            final_notices = Post.objects.filter(
                pickup_date__range=[today, day_after_tomorrow],
                cancelled=False,
                reminder=False
            ).filter(
                Q(paid__isnull=True) | Q(paid__exact="")
            ).exclude(
                cash=True
            )

            for notice in final_notices:

                if not notice.contact:
                    continue

                formatted_number = normalize_phone(notice.contact)

                if not formatted_number:
                    sms_logger.warning(f"[INVALID NUMBER] {notice.name}")
                    continue

                sms_message = (
                    "EasyGo - Urgent notice\n\n"
                    "We haven't received your payment and a response to our emails.\n"
                    "Please email us ASAP to ensure your booking remains confirmed.\n"
                    "Reply only via email >> info@easygoshuttle.com.au"
                )

                sms_sent = False

                # =========================
                # SMS
                # =========================
                try:
                    client.messages.create(
                        body=sms_message,
                        messaging_service_sid=messaging_service_sid,
                        to=formatted_number
                    )

                    sms_logger.info(f"[SMS SENT] {notice.name} {formatted_number}")
                    sms_sent = True

                except TwilioRestException as e:
                    sms_logger.error(
                        f"[SMS ERROR] {notice.name} {formatted_number} "
                        f"code={e.code} msg={e.msg}"
                    )

                # =========================
                # WhatsApp fallback
                # =========================
                if not sms_sent and notice.direction == 'Pickup from Intl Airport':
                    try:
                        client.messages.create(
                            body=sms_message,
                            from_=f'whatsapp:{whatsapp_from}',
                            to=f'whatsapp:{formatted_number}'
                        )

                        sms_logger.info(f"[WA SENT] {notice.name} {formatted_number}")

                    except TwilioRestException as e:
                        sms_logger.error(
                            f"[WA ERROR] {notice.name} {formatted_number} "
                            f"code={e.code} msg={e.msg}"
                        )

                # =========================
                # STATUS UPDATE
                # =========================
                notice.pending = True
                notice.reminder = True
                notice.save(update_fields=['pending', 'reminder'])

            self.stdout.write(
                self.style.SUCCESS('Final notices processed successfully.')
            )

        except Exception as e:
            sms_logger.error(f'Critical error in handle: {str(e)}')
            self.stdout.write(
                self.style.ERROR('Failed to process final notices')
            )