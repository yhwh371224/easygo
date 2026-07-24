import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.models import Post
from blog import dunning
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email, collect_recipients


logger = logging.getLogger(__name__)


def _has_company(booking):
    return bool((booking.company_name or '').strip())


class Command(BaseCommand):
    help = (
        '결제 미완료/부족 부킹에 픽업 시각 기준 단계별 독촉 메일 발송.\n'
        '완전 미결제: Payment notice → Urgent notice(dep 72h/arr 96h) → '
        'Final notice(dep 48h/arr 72h, 자동취소 예고). 각 단계 1회만.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='실제 발송 없이 대상/단계만 출력',
        )

    def get_display_date(self, booking):
        if booking.return_pickup_time == 'x':
            if booking.return_pickup_date and booking.return_pickup_date < date.today():
                return str(booking.pickup_date)
            else:
                return f"{booking.pickup_date} & {booking.return_pickup_date}"
        return str(booking.pickup_date)

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        today = date.today()
        # 오늘~+21일. 픽업 시각 기준 단계(Urgent/Final)는 모두 며칠 내이므로 이 창 안에 포함됨.
        start_date = today
        end_date = today + timedelta(days=21)

        bookings = Post.objects.filter(
            pickup_date__range=(start_date, end_date),
            cash=False,
            cancelled=False,
        )

        for booking in bookings:
            display_date = self.get_display_date(booking)

            try:
                price = float(booking.price or 0)
                paid = float(booking.paid or 0)

                # ----------------------------------------------------------
                # 1. 완전 미결제 → 단계별 1회 독촉 (Final → Urgent → Payment 순 판정)
                #    한 번 실행에 한 통만. 다음 실행에서 다음 단계로 진행.
                # ----------------------------------------------------------
                if booking.paid is None or booking.paid == "" or paid == 0:
                    stage = self._pick_unpaid_stage(booking)
                    if stage is None:
                        continue

                    subject, template, sent_field, extra_ctx = stage
                    if dry_run:
                        h = dunning.hours_until_pickup(booking)
                        self.stdout.write(
                            f"  [DRY] #{booking.id} {booking.pickup_date} "
                            f"arrival={dunning.is_airport_arrival(booking)} "
                            f"h_to_pickup={h:.1f} → {sent_field}"
                        )
                        continue

                    context = {
                        'booker_name': booking.booker_name,
                        'name': booking.name,
                        'email': booking.email,
                        'price': booking.price,
                        'pickup_date': booking.pickup_date,
                        'return_pickup_date': booking.return_pickup_date,
                        'display_date': display_date,
                        'prepay': booking.prepay,
                    }
                    context.update(extra_ctx)

                    recipients = collect_recipients(booking.booker_email or booking.email)
                    # 자동취소 예고(Final notice)는 내부에도 참조 사본을 보낸다.
                    if sent_field == 'final_notice_sent_at':
                        recipients = collect_recipients(
                            booking.booker_email or booking.email, RECIPIENT_EMAIL
                        )
                    if not recipients:
                        logger.warning(f"no_payment_yet: no recipients for #{booking.id}")
                        continue

                    send_template_email(subject, template, context, recipients)
                    setattr(booking, sent_field, timezone.now())
                    booking.save(update_fields=[sent_field])

                # ----------------------------------------------------------
                # 2. 부분 결제(디파짓으로 예고된 부분결제는 제외, 진짜 차액만)
                #    픽업 2일 전 안내 1회 + 1일 전 최종 1회. dedup 필드로 재발송 방지.
                # ----------------------------------------------------------
                elif 0 < paid < price:
                    deposit_due = booking.deposit_amount_due
                    deposit_satisfied = deposit_due is not None and paid >= float(deposit_due)
                    if deposit_satisfied:
                        continue

                    diff = round(price - paid, 2)
                    days_before_pickup = (booking.pickup_date - today).days

                    if days_before_pickup <= 2 and booking.discrepancy_notice_sent_at is None:
                        if dry_run:
                            self.stdout.write(f"  [DRY] #{booking.id} discrepancy_notice diff={diff}")
                            continue
                        send_template_email(
                            "Urgent notice for payment discrepancy",
                            "html_email-response-discrepancy.html",
                            {
                                'booker_name': booking.booker_name,
                                'name': booking.name,
                                'price': booking.price,
                                'paid': booking.paid,
                                'diff': diff,
                                'pickup_date': booking.pickup_date,
                                'return_pickup_date': booking.return_pickup_date,
                                'display_date': display_date,
                            },
                            collect_recipients(booking.booker_email or booking.email)
                        )
                        booking.discrepancy_notice_sent_at = timezone.now()
                        booking.save(update_fields=['discrepancy_notice_sent_at'])

                    elif days_before_pickup <= 1 and booking.discrepancy_final_sent_at is None:
                        if dry_run:
                            self.stdout.write(f"  [DRY] #{booking.id} discrepancy_final diff={diff}")
                            continue
                        send_template_email(
                            "Final notice: outstanding balance on your booking",
                            "html_email-response-discrepancy-final.html",
                            {
                                'booker_name': booking.booker_name,
                                'name': booking.name,
                                'price': booking.price,
                                'paid': booking.paid,
                                'diff': diff,
                                'pickup_date': booking.pickup_date,
                                'return_pickup_date': booking.return_pickup_date,
                                'display_date': display_date,
                            },
                            collect_recipients(booking.booker_email or booking.email)
                        )
                        booking.discrepancy_final_sent_at = timezone.now()
                        booking.save(update_fields=['discrepancy_final_sent_at'])

            except Exception as e:
                logger.error(f"Failed to send email for booking {booking.id} ({booking.email}): {e}")
                self.stdout.write(self.style.ERROR(f"Failed to send email for {booking.email}: {e}"))

        self.stdout.write(self.style.SUCCESS('No_payment_yet emailed successfully'))

    def _pick_unpaid_stage(self, booking):
        """완전 미결제 건에서 지금 발송해야 할 단계를 반환. 없으면 None.

        반환: (subject, template, sent_field, extra_context)
        판정 순서: Final(가장 임박) → Urgent → Payment(가장 이름). 각 단계 1회만.
        """
        # 3단계: Final notice (자동취소 예고). 기업(company_name) 고객은 인보이스
        #        처리라 자동취소 대상이 아니므로 취소 예고도 보내지 않는다.
        if (
            booking.final_notice_sent_at is None
            and not _has_company(booking)
            and dunning.is_final_notice_due(booking)
        ):
            deadline = dunning.cancel_deadline(booking)
            return (
                "Final notice — payment required to keep your booking",
                "html_email-final-warning.html",
                "final_notice_sent_at",
                {
                    'is_arrival': dunning.is_airport_arrival(booking),
                    'deadline': deadline,
                },
            )

        # 2단계: Urgent notice.
        if (
            booking.no_payment_urgent_sent_at is None
            and dunning.is_urgent_notice_due(booking)
        ):
            return (
                "Urgent notice for payment",
                "html_email-nopayment-today.html",
                "no_payment_urgent_sent_at",
                {},
            )

        # 1단계: Payment notice (가장 부드러운 초기 안내).
        if booking.no_payment_notice_sent_at is None:
            return (
                "Payment notice",
                "html_email-nopayment.html",
                "no_payment_notice_sent_at",
                {},
            )

        return None
