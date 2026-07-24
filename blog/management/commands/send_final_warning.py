import logging

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from blog.models import Post
from blog import dunning
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email, collect_recipients

logger = logging.getLogger(__name__)

# 픽업 시각 기준 독촉 사다리(no_payment_yet)는 픽업 21일 이내부터 작동한다.
# 이 명령은 그보다 먼 미래 예약(사다리 창 밖)에서 미결제·무응답인 건에
# "예약 pending 상태" 를 한 번 알려주는 조기 안내만 담당한다(겹치지 않게).
LADDER_WINDOW_DAYS = 21


class Command(BaseCommand):
    help = (
        '사다리 창(픽업 21일) 밖의 먼 미래 미결제·무응답 예약에 '
        '"예약 pending 상태" 조기 안내 1회 발송. '
        '(픽업 임박 독촉/취소는 no_payment_yet + auto_cancel_pending 이 담당)'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='실제 발송 없이 대상 목록만 출력',
        )
        parser.add_argument(
            '--hours', type=int, default=48,
            help='무응답 기준 시간 (기본값: 48시간)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours = options['hours']
        now = timezone.now()
        cutoff = now - timedelta(hours=hours)
        window_end = date.today() + timedelta(days=LADDER_WINDOW_DAYS)

        # 조기 pending 안내 대상:
        #   reminder=False        → 아직 고객 응답 없음
        #   cash=False            → 캐쉬 미선택
        #   cancelled=False       → 아직 취소 안 됨
        #   paid 없음             → 결제 미완료
        #   company_name 없음     → 기업 고객 제외 (인보이스 처리)
        #   final_warning_at 없음 → 아직 조기 안내 안 보냄 (dedup)
        #   created <= cutoff     → 48시간 이상 무응답
        #   pickup_date > 창 끝    → 사다리 창 밖 (임박건은 no_payment_yet 담당)
        qs = Post.objects.filter(
            reminder=False,
            cash=False,
            cancelled=False,
            final_warning_at__isnull=True,
            created__lte=cutoff,
            pickup_date__gt=window_end,
        ).filter(
            Q(paid__isnull=True) | Q(paid='')
        ).filter(
            Q(company_name__isnull=True) | Q(company_name='')
        ).order_by('pickup_date', 'created')

        count = qs.count()
        label = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(
            f"\n{label}pending 조기 안내 대상: {count}건 "
            f"(무응답 {hours}h 경과, 픽업 {LADDER_WINDOW_DAYS}일 초과)\n"
        )

        sent = 0
        for notice in qs:
            self.stdout.write(
                f"  #{notice.id:<6} {str(notice.pickup_date)} {notice.pickup_time or '':<8} "
                f"{notice.name:<20} prepay={notice.prepay}"
            )
            if dry_run:
                continue
            try:
                if notice.booker_email:
                    recipients = collect_recipients(notice.booker_email, RECIPIENT_EMAIL)
                else:
                    recipients = collect_recipients(notice.email, notice.email1, RECIPIENT_EMAIL)
                if not recipients:
                    logger.warning('send_final_warning: no recipients for Post pk=%s', notice.pk)
                    continue

                send_template_email(
                    "Your booking is pending — payment required to confirm",
                    "html_email-nopayment.html",
                    {
                        'booker_name': notice.booker_name,
                        'name': notice.name,
                        'email': notice.email,
                        'price': notice.price,
                        'pickup_date': notice.pickup_date,
                        'return_pickup_date': notice.return_pickup_date,
                        'display_date': str(notice.pickup_date),
                        'prepay': notice.prepay,
                    },
                    recipients,
                )
                notice.final_warning_at = now
                notice.save(update_fields=['final_warning_at'])
                sent += 1
                logger.info(
                    'send_final_warning(pending-nudge): Post pk=%s email=%s pickup_date=%s',
                    notice.pk, notice.email, notice.pickup_date,
                )
            except Exception as e:
                logger.error('send_final_warning: failed for Post pk=%s: %s', notice.pk, e)
                self.stdout.write(self.style.ERROR(f"Failed for #{notice.id}: {e}"))

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n[DRY RUN] 실제 발송 없음. {count}건 대상 확인 완료.\n'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n완료: {sent}건 pending 조기 안내 발송.\n'))
