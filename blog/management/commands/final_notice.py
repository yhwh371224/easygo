import logging
import os

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.db.models import Q
from blog.models import Post
from blog.sms_utils import send_sms_notice, send_whatsapp_template
from main.settings import RECIPIENT_EMAIL
from basecamp.utils import render_email_template

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
    help = 'Send final notice emails + WhatsApp/SMS reminders'

    def handle(self, *args, **options):
        try:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            within_three_days = today + timedelta(days=3)

            final_notices = Post.objects.filter(
                pickup_date__range=(tomorrow, within_three_days),
                cancelled=False,
            ).filter(
                Q(paid__isnull=True) | Q(paid__exact="")
            ).exclude(
                cash=True
            )

            for notice in final_notices:
                try:
                    # 1️⃣ 이메일 발송
                    html_content = render_email_template("html_email-fnotice.html", {
                        'name': notice.name,
                        'email': notice.email
                    })
                    text_content = strip_tags(html_content)

                    recipients = [addr for addr in [notice.email, notice.email1, RECIPIENT_EMAIL] if addr]
                    if recipients:
                        email = EmailMultiAlternatives("Final notice", text_content, '', recipients)
                        email.attach_alternative(html_content, "text/html")
                        email.send()
                        sms_logger.info(f"Email sent to {notice.email}")

                    # 2️⃣ SMS / WhatsApp 발송 (cash=False만)
                    if notice.contact:
                        sms_message = (
                            "EasyGo - Urgent notice\n\n"
                            "We haven't received your payment or reply to our emails.\n"
                            "Please email us ASAP to ensure your booking remains confirmed.\n"
                            "Reply only via email >> info@easygoshuttle.com.au"
                        )
                        send_sms_notice(notice.contact, sms_message)
                        if notice.direction == 'Pickup from Intl Airport':
                            send_whatsapp_template(notice.contact, user_name=notice.name)

                    # 3️⃣ pending 표시
                    notice.pending = True
                    notice.save()

                except Exception as e:
                    sms_logger.error(f"Failed to send email/SMS/WhatsApp for {notice.email}: {e}")

            self.stdout.write(self.style.SUCCESS('All final notices sent (email + SMS/WhatsApp).'))

        except Exception as e:
            sms_logger.error(f'Error in handle method: {e}')
            self.stdout.write(self.style.ERROR('Failed to send final notices'))
