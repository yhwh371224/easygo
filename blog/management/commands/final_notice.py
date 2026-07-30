import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from blog.models import Post
from blog.blog_utils import booking_balance, is_deposit_satisfied
from blog.sms_utils import send_sms_notice, send_whatsapp_template

sms_logger = logging.getLogger('sms')


class Command(BaseCommand):
    help = (
        '픽업 임박(오늘~내일) 미납 부킹에 마지막 SMS 에스컬레이션.\n'
        '  · 완전 미결제: 무응답(reminder=False) 건만\n'
        '  · 부분 결제(short payment): 차액 안내 메일을 이미 보낸 건만\n'
        '(Final notice 이메일 및 잔액부족 안내 이메일은 no_payment_yet 이 픽업 시각 '
        '기준으로 이미 발송하므로 여기서는 중복 이메일 없이 SMS 채널만 담당한다.)'
    )

    def handle(self, *args, **options):
        try:
            today = date.today()
            within_one_day = today + timedelta(days=1)

            base = Post.objects.filter(
                pickup_date__range=(today, within_one_day),
                cancelled=False,
                cash=False,
            ).filter(
                # 기업 고객 제외 (인보이스 처리)
                Q(company_name__isnull=True) | Q(company_name__exact="")
            )

            # ── 1. 완전 미결제 + 무응답 ──
            #   reminder=False → 아직 응답 없음 (응답한 손님에겐 SMS 안 함)
            unpaid = base.filter(
                pending=True,
                reminder=False,
            ).filter(
                Q(paid__isnull=True) | Q(paid__exact="")
            )

            for notice in unpaid:
                self._send(
                    notice,
                    "EasyGo - Urgent notice\n\n"
                    "We haven't received your payment or reply to our emails.\n"
                    "Please email us ASAP to ensure your booking remains confirmed.\n"
                    "Reply only via email >> info@easygoshuttle.com.au",
                    label='unpaid',
                )

            # ── 2. 부분 결제(short payment) ──
            #   결제가 들어오면 reminder=True / pending=False 로 바뀌므로 위 필터에
            #   걸리지 않는다. 대신 차액 안내 메일을 이미 보낸 건(= 손님이 이메일로
            #   충분히 고지받은 건)만 SMS 로 마지막 에스컬레이션.
            partial = base.filter(
                Q(discrepancy_notice_sent_at__isnull=False)
                | Q(discrepancy_final_sent_at__isnull=False)
            ).exclude(
                Q(paid__isnull=True) | Q(paid__exact="")
            )

            for notice in partial:
                amounts = booking_balance(notice)
                if amounts is None:
                    continue  # 금액 판정 불가(비숫자 텍스트) → 수동 처리 영역
                _, paid, balance = amounts
                # 이미 잔액을 낸 손님, 디파짓으로 예고된 부분결제는 제외.
                if paid <= 0 or balance <= 0 or is_deposit_satisfied(notice):
                    continue
                self._send(
                    notice,
                    "EasyGo - Urgent notice\n\n"
                    f"Your booking still has an outstanding balance of ${balance:.2f}.\n"
                    "Please settle it ASAP to ensure your booking remains confirmed.\n"
                    "Reply only via email >> info@easygoshuttle.com.au",
                    label='short-payment',
                )

            self.stdout.write(self.style.SUCCESS('Final-notice SMS escalation done.'))

        except Exception as e:
            sms_logger.error(f'Error in final_notice handle: {e}')
            self.stdout.write(self.style.ERROR('Failed to send final-notice SMS'))

    def _send(self, notice, sms_message, label):
        try:
            if not notice.contact:
                return
            send_sms_notice(notice.contact, sms_message)
            sms_logger.info(
                f"Final-notice SMS ({label}) sent to {notice.contact} (#{notice.id})"
            )
            if notice.direction == 'Pickup from Intl Airport':
                # DISABLED: Twilio WhatsApp sending — do not uncomment without approval
                pass  # send_whatsapp_template(notice.contact, user_name=notice.name)

        except Exception as e:
            sms_logger.error(f"Failed to send final-notice SMS for {notice.email}: {e}")
