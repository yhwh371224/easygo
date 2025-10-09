import os
import logging
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import Q
from twilio.rest import Client
from decouple import config
from blog.models import Post
from main.settings import RECIPIENT_EMAIL

# Logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
sms_logger = logging.getLogger('sms')
sms_logger.setLevel(logging.INFO)

# 파일 핸들러 추가
fh = logging.FileHandler(os.path.join(LOG_DIR, 'sms.log'))
fh.setLevel(logging.INFO)
formatter = logging.Formatter('{levelname} {asctime} {message}', style='{')
fh.setFormatter(formatter)

if not sms_logger.handlers:  # 중복 핸들러 방지
    sms_logger.addHandler(fh)

class Command(BaseCommand):
    help = 'Send final notice emails + WhatsApp/SMS reminders'

    def handle(self, *args, **options):
        try:
            today = date.today()
            within_three_days = today + timedelta(days=3)

            final_notices = Post.objects.filter(
                pickup_date__range=(today, within_three_days),
                cancelled=False,
                reminder=False
            ).filter(
                Q(paid__isnull=True) | Q(paid__exact="")
            )

            # Twilio setup
            account_sid = config('TWILIO_ACCOUNT_SID')
            auth_token = config('TWILIO_AUTH_TOKEN')
            sms_from = config('TWILIO_SMS_FROM')
            whatsapp_from = config('TWILIO_WHATSAPP_FROM')
            client = Client(account_sid, auth_token)

            def format_phone_number(phone_number):
                if not phone_number:
                    return None
                phone_number = phone_number.strip()
                if phone_number.startswith('+'):
                    return phone_number
                elif phone_number.startswith('0'):
                    return '+61' + phone_number[1:]
                else:
                    return '+' + phone_number

            def send_whatsapp_message(sendto, name, email, price):
                formatted_number = format_phone_number(sendto)
                if not formatted_number:
                    return
                try:
                    client.messages.create(
                        body=(
                            "EasyGo - Urgent notice\n\n"
                            "We haven't received your response to our emails.\n"
                            "Please email us ASAP to ensure your booking remains confirmed.\n"
                            "Reply only via email >> info@easygoshuttle.com.au"
                        ),
                        from_=whatsapp_from,
                        to=f'whatsapp:{formatted_number}'
                    )
                    sms_logger.info(f"WhatsApp sent to {name} ({email}) at {formatted_number} | Price: ${price}")
                except Exception as e:
                    sms_logger.error(f"Failed to send WhatsApp to {name} ({email}) at {formatted_number} | Error: {e}")

            def send_sms_message(sendto, name, email, price):
                formatted_number = format_phone_number(sendto)
                if not formatted_number:
                    return
                try:
                    client.messages.create(
                        body=(
                            "EasyGo - Urgent notice\n\n"
                            "We haven't received your payment or reply to our emails.\n"
                            "Please email us ASAP to ensure your booking remains confirmed.\n"
                            "Reply only via email >> info@easygoshuttle.com.au"
                        ),
                        from_=sms_from,
                        to=formatted_number
                    )
                    sms_logger.info(f"SMS sent to {name} ({email}) at {formatted_number} | Price: ${price}")
                except Exception as e:
                    sms_logger.error(f"Failed to send SMS to {name} ({email}) at {formatted_number} | Error: {e}")

            # Process each notice
            for notice in final_notices:
                # 1️⃣ Send Email
                try:
                    template_name = "basecamp/html_email-fnotice.html"
                    html_content = render_to_string(template_name, {
                        'name': notice.name,
                        'email': notice.email
                    })
                    text_content = strip_tags(html_content)

                    recipients = [addr for addr in [notice.email, notice.email1, RECIPIENT_EMAIL] if addr]
                    email = EmailMultiAlternatives(
                        "Final notice",
                        text_content,
                        '',
                        recipients
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send()

                    sms_logger.info(f"Email sent to {notice.email}")

                    # 2️⃣ After email, send SMS and WhatsApp
                    if notice.contact:
                        send_sms_message(notice.contact, notice.name, notice.email, notice.price)
                        if notice.direction == 'Pickup from Intl Airport':
                            send_whatsapp_message(notice.contact, notice.name, notice.email, notice.price)

                    # 3️⃣ Mark as pending
                    notice.pending = True
                    notice.save()

                except Exception as e:
                    sms_logger.error(f"Failed to send email/SMS for {notice.email}: {e}")

            self.stdout.write(self.style.SUCCESS('All final notices sent (email + SMS/WhatsApp).'))

        except Exception as e:
            sms_logger.error(f'Error in handle method: {e}')
            self.stdout.write(self.style.ERROR('Failed to send final notices'))
