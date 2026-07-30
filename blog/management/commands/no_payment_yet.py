import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.models import Post
from blog import dunning
from blog.blog_utils import booking_balance, is_deposit_satisfied
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email, collect_recipients


logger = logging.getLogger(__name__)


def _has_company(booking):
    return bool((booking.company_name or '').strip())


class Command(BaseCommand):
    help = (
        '결제 미완료/부족 부킹에 픽업 시각 기준 단계별 독촉 메일 발송.\n'
        '완전 미결제: Payment notice → Urgent notice(dep 72h/arr 96h) → '
        'Final notice(dep 48h/arr 72h, 자동취소 예고). 각 단계 1회만.\n'
        '부분 결제(short payment): Discrepancy notice(dep 72h/arr 96h) → '
        'Discrepancy final(dep 48h/arr 72h, 자동취소 예고). 각 단계 1회만.\n'
        '금액 판정은 blog_utils.booking_balance(surcharge/discount 반영) 사용.'
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
                # 픽업이 이미 지난 건에는 어떤 결제 독촉도 보내지 않는다.
                # (쿼리셋이 오늘을 포함하므로 오늘 픽업이 지난 건이 섞일 수 있음)
                h_to_pickup = dunning.hours_until_pickup(booking)
                if h_to_pickup is not None and h_to_pickup <= 0:
                    continue

                # surcharge/discount 를 반영한 실제 청구액 기준으로 판정한다.
                # (결제 배분 blog_utils.process_generic_payment 및 온라인 잔액결제
                #  basecamp.views.payments 와 동일한 공식 — 셋이 어긋나면 완납인데
                #  독촉이 나가거나 잔액이 실제와 다르게 표시된다.)
                amounts = booking_balance(booking)
                if amounts is None:
                    # price/paid 가 비숫자 텍스트 → 금액 판정 불가, 수동 처리 영역.
                    logger.warning(
                        f"no_payment_yet: skipped #{booking.id} — "
                        f"non-numeric price={booking.price!r} paid={booking.paid!r}"
                    )
                    continue
                total, paid, balance = amounts

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
                # 2. 부분 결제(short payment) → 단계별 1회 독촉.
                #    디파짓 인보이스로 예고된 부분결제는 제외, 진짜 차액만.
                #    미결제 사다리와 같은 픽업 시각 기준(dep 72h/48h, arr 96h/72h)
                #    이라 discrepancy final ↔ 자동취소 사이 GRACE_HOURS 가 보장된다.
                # ----------------------------------------------------------
                elif balance > 0:
                    if is_deposit_satisfied(booking):
                        continue

                    stage = self._pick_partial_stage(booking)
                    if stage is None:
                        continue

                    subject, template, sent_field = stage
                    if dry_run:
                        h = dunning.hours_until_pickup(booking)
                        self.stdout.write(
                            f"  [DRY] #{booking.id} {booking.pickup_date} "
                            f"arrival={dunning.is_airport_arrival(booking)} "
                            f"h_to_pickup={h:.1f} balance={balance} → {sent_field}"
                        )
                        continue

                    context = {
                        'booker_name': booking.booker_name,
                        'name': booking.name,
                        # 표시 금액도 surcharge/discount 반영분으로 통일 —
                        # price - paid = diff 가 메일 안에서 항상 맞아떨어지게.
                        'price': f"{total:.2f}",
                        'paid': f"{paid:.2f}",
                        'diff': f"{balance:.2f}",
                        'pickup_date': booking.pickup_date,
                        'return_pickup_date': booking.return_pickup_date,
                        'display_date': display_date,
                    }

                    recipients = collect_recipients(booking.booker_email or booking.email)
                    # 자동취소 예고 단계는 내부에도 참조 사본을 보낸다(미결제 final 과 동일).
                    if sent_field == 'discrepancy_final_sent_at':
                        recipients = collect_recipients(
                            booking.booker_email or booking.email, RECIPIENT_EMAIL
                        )
                    if not recipients:
                        logger.warning(f"no_payment_yet: no recipients for #{booking.id}")
                        continue

                    send_template_email(subject, template, context, recipients)
                    setattr(booking, sent_field, timezone.now())
                    booking.save(update_fields=[sent_field])

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
            and booking.final_notice_sent_at is None
            and dunning.is_urgent_notice_due(booking)
        ):
            return (
                "Urgent notice for payment",
                "html_email-nopayment-today.html",
                "no_payment_urgent_sent_at",
                {},
            )

        # 1단계: Payment notice (가장 부드러운 초기 안내).
        #   이 단계만 시각 게이트가 없다 — 21일 창에 들어온 미결제 건은 언제든
        #   1회 받아야 하기 때문. 그래서 임박 예약(생성 시점이 이미 Urgent/Final
        #   창 안)에서는 강한 단계가 먼저 나간 뒤 이 부드러운 안내가 뒤따라 나가는
        #   역순이 생긴다. 이미 더 강한 경고를 보냈으면 보내지 않는다.
        if (
            booking.no_payment_notice_sent_at is None
            and booking.no_payment_urgent_sent_at is None
            and booking.final_notice_sent_at is None
        ):
            return (
                "Payment notice",
                "html_email-nopayment.html",
                "no_payment_notice_sent_at",
                {},
            )

        return None

    def _pick_partial_stage(self, booking):
        """부분 결제(short payment) 건에서 지금 발송해야 할 단계를 반환. 없으면 None.

        반환: (subject, template, sent_field)
        판정 순서: Final(가장 임박) → Notice. 각 단계 1회만.
        결제 직후 1차 안내는 blog_utils.process_generic_payment 이 이미 보내므로
        여기서는 픽업이 다가올 때의 후속 에스컬레이션만 담당한다.
        """
        # 2단계: Discrepancy final (자동취소 예고). 기업 고객은 인보이스 처리라
        #        자동취소 대상이 아니므로 취소 예고도 보내지 않는다.
        if (
            booking.discrepancy_final_sent_at is None
            and not _has_company(booking)
            and dunning.is_final_notice_due(booking)
        ):
            return (
                "Final notice: outstanding balance on your booking",
                "html_email-response-discrepancy-final.html",
                "discrepancy_final_sent_at",
            )

        # 1단계: Discrepancy notice.
        #   미결제 사다리의 1단계(Payment notice)와 달리 이 단계도 시각 게이트가
        #   걸려 있어서, 픽업 임박 상태에서 처음 부분결제가 들어온 건은 2단계가
        #   먼저 나갈 수 있다. 그 뒤에 더 약한 1단계를 보내면 순서가 거꾸로이므로
        #   final 을 이미 보낸 건에는 1단계를 보내지 않는다.
        if (
            booking.discrepancy_notice_sent_at is None
            and booking.discrepancy_final_sent_at is None
            and dunning.is_urgent_notice_due(booking)
        ):
            return (
                "Urgent notice for payment discrepancy",
                "html_email-response-discrepancy.html",
                "discrepancy_notice_sent_at",
            )

        return None
