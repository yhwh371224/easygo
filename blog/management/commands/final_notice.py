import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from blog.models import Post
from blog.blog_utils import _net_adjustment
from blog.sms_utils import send_sms_notice, send_whatsapp_template
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email, collect_recipients

sms_logger = logging.getLogger('sms')


class Command(BaseCommand):
    help = 'Send final notice emails + WhatsApp/SMS reminders'

    def handle(self, *args, **options):
        try:
            today = date.today()
            within_one_day = today + timedelta(days=1)

            final_notices = Post.objects.filter(
                pickup_date__range=(today, within_one_day),
                cancelled=False,
                pending=True,
            ).filter(
                Q(paid__isnull=True) | Q(paid__exact="")
            ).exclude(
                Q(cash=True) | Q(reminder=True)
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
                            # DISABLED: Twilio WhatsApp sending — do not uncomment without approval
                            pass  # send_whatsapp_template(notice.contact, user_name=notice.name)

                    # 3️⃣ pending 표시
                    notice.pending = True
                    notice.save()

                except Exception as e:
                    sms_logger.error(f"Failed to send email/SMS/WhatsApp for {notice.email}: {e}")

            # ─────────────────────────────────────────────────────────────
            # 잔액 부족(short payment) 안내 — 부분 결제됐지만 잔액이 남은 건.
            # stale 할 수 있는 toll 플래그 대신 price/paid 로 매번 실시간 재계산한다
            # (판정 공식은 blog_utils.process_generic_payment 와 동일).
            # 완전 미결제 건은 위 final_notice 가 처리하므로 여기서는 paid 값이
            # 있는(부분 결제) 건만 대상으로 한다. 캐쉬·기업(company_name) 제외.
            # short_payment_notified_at 이 없는 건만 → 이미 안내한 건 재발송 방지.
            short_payments = Post.objects.filter(
                pickup_date__range=(today, within_one_day),
                cancelled=False,
                short_payment_notified_at__isnull=True,
            ).exclude(
                Q(cash=True) | Q(paid__isnull=True) | Q(paid__exact="")
            )

            for notice in short_payments:
                try:
                    if (notice.company_name or '').strip():
                        continue  # 기업 고객 — 인보이스로 별도 처리

                    surcharge, discount = _net_adjustment(notice)
                    p_total = round(float(notice.price or 0) + surcharge - discount, 2)
                    p_paid = float(notice.paid or 0)
                    balance = round(p_total - p_paid, 2)
                    if balance <= 0:
                        continue  # 잔액 없음 — 안내 불필요

                    if notice.booker_email:
                        recipients = collect_recipients(notice.booker_email, RECIPIENT_EMAIL)
                    else:
                        recipients = collect_recipients(notice.email, notice.email1, RECIPIENT_EMAIL)
                    if not recipients:
                        continue

                    send_template_email(
                        "Outstanding balance on your booking - EasyGo",
                        "html_email-response-discrepancy.html",
                        {
                            'booker_name': notice.booker_name,
                            'name': notice.name,
                            'price': f"{p_total:.2f}",
                            'paid': f"{p_paid:.2f}",
                            'diff': f"{balance:.2f}",
                        },
                        recipients,
                    )
                    notice.short_payment_notified_at = timezone.now()
                    notice.save(update_fields=['short_payment_notified_at'])
                    sms_logger.info(f"Short-payment notice sent to {notice.email} (balance ${balance:.2f})")

                except Exception as e:
                    sms_logger.error(f"Failed to send short-payment notice for {notice.email}: {e}")

            self.stdout.write(self.style.SUCCESS('All final notices sent (email + SMS/WhatsApp).'))

        except Exception as e:
            sms_logger.error(f'Error in handle method: {e}')
            self.stdout.write(self.style.ERROR('Failed to send final notices'))
