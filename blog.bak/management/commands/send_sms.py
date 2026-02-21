import os
import logging
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from blog.models import Post
from blog.sms_utils import send_sms_notice, send_whatsapp_template

# Logger setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

sms_logger = logging.getLogger('sms')
sms_logger.setLevel(logging.INFO)
if not sms_logger.handlers:
    fh = logging.FileHandler(os.path.join(LOG_DIR, 'sms.log'))
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('{levelname} {asctime} {message}', style='{')
    fh.setFormatter(formatter)
    sms_logger.addHandler(fh)


class Command(BaseCommand):
    help = 'Send final notices via WhatsApp or SMS for unpaid future bookings (cash excluded)'

    def handle(self, *args, **options):
        try:
            today = date.today()
            day_after_tomorrow = today + timedelta(days=3)

            # cash=False, unpaid, 미래 부킹
            final_notices = Post.objects.filter(
                pickup_date__range=[today, day_after_tomorrow],
                cancelled=False,
                reminder=False,
            ).filter(
                Q(paid__isnull=True) | Q(paid__exact="")
            ).exclude(
                cash=True
            )

            for notice in final_notices:
                try:
                    if notice.contact:
                        # SMS 메시지
                        sms_message = (
                            "EasyGo - Urgent notice\n\n"
                            "We haven't received your payment and a response to our emails.\n"
                            "Please email us ASAP to ensure your booking remains confirmed\n"
                            "Reply only via email >> info@easygoshuttle.com.au"
                        )
                        send_sms_notice(notice.contact, sms_message)
                        sms_logger.info(f"SMS sent to {notice.name} ({notice.contact})")

                        # WhatsApp 메시지 (국제공항 픽업인 경우만)
                        if notice.direction == 'Pickup from Intl Airport':
                            send_whatsapp_template(notice.contact, user_name=notice.name)
                            sms_logger.info(f"WhatsApp sent to {notice.name} ({notice.contact})")

                    # pending 표시
                    notice.pending = True
                    notice.save()

                except Exception as e:
                    sms_logger.error(f"Failed to send SMS/WhatsApp for {notice.name} ({notice.contact}): {e}")

            self.stdout.write(self.style.SUCCESS('All Twilio final notices sent successfully.'))

        except Exception as e:
            sms_logger.error(f'Error in handle method: {e}')
            self.stdout.write(self.style.ERROR('Failed to send Twilio final notices'))
