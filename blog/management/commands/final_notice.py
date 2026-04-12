import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from blog.models import Post
from blog.sms_utils import send_sms_notice, send_whatsapp_template
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email, collect_recipients

sms_logger = logging.getLogger('sms')


class Command(BaseCommand):
    help = 'Send final notice emails + WhatsApp/SMS reminders'

    def handle(self, *args, **options):
        try:
            today = date.today()
            within_three_days = today + timedelta(days=3)

            final_notices = Post.objects.filter(
                pickup_date__range=(today, within_three_days),
                cancelled=False,
            ).filter(
                Q(paid__isnull=True) | Q(paid__exact="")
            ).filter(
                Q(reminder=False) | Q(pending=True)
            )

            for notice in final_notices:
                try:
                    # 1️⃣ 이메일 발송
                    if notice.booker_email:
                        recipients = collect_recipients(notice.booker_email, RECIPIENT_EMAIL)
                    else:
                        recipients = collect_recipients(notice.email, notice.email1, RECIPIENT_EMAIL)
                    if recipients:
                        send_template_email(
                            "Final notice",
                            "html_email-fnotice.html",
                            {'booker_name': notice.booker_name, 'name': notice.name, 'email': notice.email},
                            recipients,
                        )
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
