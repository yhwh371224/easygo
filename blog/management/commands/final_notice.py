import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from blog.models import Post
from blog.blog_utils import booking_balance, is_deposit_protected
from blog.sms_utils import send_sms_notice, send_whatsapp_template

sms_logger = logging.getLogger('sms')


class Command(BaseCommand):
    help = (
        '픽업 임박(오늘~내일) 미납 부킹에 마지막 SMS 에스컬레이션.\n'
        '  · 완전 미결제: 취소 예고 메일(final_notice_sent_at)을 이미 보낸 건만\n'
        '  · 부분 결제(short payment): 차액 안내 메일을 이미 보낸 건만\n'
        'SMS 는 부킹당 총 1통 — send_sms 가 이미 보냈으면(sms_notice_sent_at) '
        '여기서는 보내지 않는다. 두 명령이 sms_* 필드를 서로 확인한다.\n'
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

            # ── 1. 완전 미결제 ──
            #   부분결제 경로(아래)와 같은 기준: 이메일로 취소 예고(Final notice)를
            #   이미 받은 건만 SMS 로 마지막 에스컬레이션.
            #
            #   예전 필터는 pending=True + reminder=False 였는데 둘 다 못 믿는다:
            #     · update_reminder 가 "곧 낼게요" 답장 한 통에 reminder=True /
            #       pending=False 로 바꿔버려서, 미결제인데도 대상에서 빠졌다.
            #     · send_sms 가 SMS 발송 후 스스로 reminder=True 를 찍어서,
            #       SMS 를 한 번 받은 건은 영구히 대상에서 빠졌다.
            #   이메일 사다리(no_payment_yet)와 자동취소(auto_cancel_pending)는
            #   이미 reminder 를 안 보는데 SMS 만 옛 모델에 남아 있었다.
            #
            #   sms_notice_sent_at 도 함께 본다 — SMS 총량은 부킹당 1통 유지.
            #   (예전엔 send_sms 가 찍는 reminder=True 가 우연히 이 역할을 했다)
            unpaid = base.filter(
                final_notice_sent_at__isnull=False,
                sms_final_sent_at__isnull=True,
                sms_notice_sent_at__isnull=True,
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
            #   차액 안내 메일을 이미 보낸 건(= 손님이 이메일로 충분히 고지받은 건)만
            #   SMS 로 마지막 에스컬레이션.
            partial = base.filter(
                sms_final_sent_at__isnull=True,
                sms_notice_sent_at__isnull=True,
            ).filter(
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
                # 이미 잔액을 낸 손님, 그리고 아직 보호 중인 디파짓 건은 제외.
                # (취소 예고까지 나간 디파짓 건은 보호가 풀려 여기 포함된다)
                if paid <= 0 or balance <= 0 or is_deposit_protected(notice):
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
            if send_sms_notice(notice.contact, sms_message) is None:
                # 번호 오류/Twilio 실패 → 발송 기록을 남기지 않아 다음 실행에서 재시도.
                sms_logger.warning(
                    f"Final-notice SMS ({label}) failed for #{notice.id} — will retry"
                )
                return
            # 중복 발송 방지는 전용 필드로만 한다(reminder/pending 은 건드리지 않음).
            notice.sms_final_sent_at = timezone.now()
            notice.save(update_fields=['sms_final_sent_at'])
            sms_logger.info(
                f"Final-notice SMS ({label}) sent to {notice.contact} (#{notice.id})"
            )
            if notice.direction == 'Pickup from Intl Airport':
                # DISABLED: Twilio WhatsApp sending — do not uncomment without approval
                pass  # send_whatsapp_template(notice.contact, user_name=notice.name)

        except Exception as e:
            sms_logger.error(f"Failed to send final-notice SMS for {notice.email}: {e}")
