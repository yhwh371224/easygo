import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from blog.models import Post
from blog.sms_utils import send_sms_notice, send_whatsapp_template

sms_logger = logging.getLogger('sms')


class Command(BaseCommand):
    help = (
        '픽업 임박(오늘~내일) 미결제·무응답 부킹에 마지막 SMS 에스컬레이션.\n'
        '(Final notice 이메일 및 잔액부족 안내 이메일은 no_payment_yet 이 픽업 시각 '
        '기준으로 이미 발송하므로 여기서는 중복 이메일 없이 SMS 채널만 담당한다.)'
    )

    def handle(self, *args, **options):
        try:
            today = date.today()
            within_one_day = today + timedelta(days=1)

            # 완전 미결제 + 무응답 + 임박 건에만 마지막 SMS.
            #   cash=False        → 캐쉬 미선택
            #   reminder=False    → 아직 응답 없음 (응답한 손님에겐 SMS 안 함)
            #   company_name 없음 → 기업 고객 제외
            final_notices = Post.objects.filter(
                pickup_date__range=(today, within_one_day),
                cancelled=False,
                pending=True,
                cash=False,
                reminder=False,
            ).filter(
                Q(paid__isnull=True) | Q(paid__exact="")
            ).filter(
                Q(company_name__isnull=True) | Q(company_name__exact="")
            )

            for notice in final_notices:
                try:
                    if not notice.contact:
                        continue
                    sms_message = (
                        "EasyGo - Urgent notice\n\n"
                        "We haven't received your payment or reply to our emails.\n"
                        "Please email us ASAP to ensure your booking remains confirmed.\n"
                        "Reply only via email >> info@easygoshuttle.com.au"
                    )
                    send_sms_notice(notice.contact, sms_message)
                    sms_logger.info(f"Final-notice SMS sent to {notice.contact} (#{notice.id})")
                    if notice.direction == 'Pickup from Intl Airport':
                        # DISABLED: Twilio WhatsApp sending — do not uncomment without approval
                        pass  # send_whatsapp_template(notice.contact, user_name=notice.name)

                except Exception as e:
                    sms_logger.error(f"Failed to send final-notice SMS for {notice.email}: {e}")

            self.stdout.write(self.style.SUCCESS('Final-notice SMS escalation done.'))

        except Exception as e:
            sms_logger.error(f'Error in final_notice handle: {e}')
            self.stdout.write(self.style.ERROR('Failed to send final-notice SMS'))
