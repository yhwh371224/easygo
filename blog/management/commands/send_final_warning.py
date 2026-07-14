import logging

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email, collect_recipients

logger = logging.getLogger(__name__)

# 픽업이 48시간(=2일) 이내로 임박한 건은 자동 취소 흐름에서 제외하고
# final_notice(픽업 1일 전 메일+SMS)와 수동 처리에 맡긴다.
IMMINENT_PICKUP_DAYS = 2
# 최종 경고 후 자동 취소까지 주는 유예 시간(auto_cancel_pending과 맞춰야 함).
GRACE_HOURS = 24


def _is_arrival(direction):
    """공항 도착(=공항에서 픽업) 건이면 True. Sydney 도착 선결제 안내에 사용."""
    d = (direction or '').lower()
    return 'pickup from' in d and 'airport' in d


class Command(BaseCommand):
    help = (
        '컨펌 후 48시간 무응답(pending·미결제) 부킹에 최종 경고 메일 발송. '
        'final_warning_at 을 기록해 이후 auto_cancel_pending 이 유예 경과 시 취소.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 발송 없이 대상 목록만 출력',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=48,
            help='무응답 기준 시간 (기본값: 48시간)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours = options['hours']
        now = timezone.now()
        cutoff = now - timedelta(hours=hours)
        deadline = now + timedelta(hours=GRACE_HOURS)
        imminent_date = date.today() + timedelta(days=IMMINENT_PICKUP_DAYS)

        # 최종 경고 대상 (payment_options 에 의존하지 않음 — prepay 건은 생성 시
        # pending=False 라 pending 조건을 걸면 누락되므로 미결제+무응답으로 판단):
        #   reminder=False      → 아직 고객 응답 없음
        #   cash=False          → 캐쉬 미선택 (선택했으면 확정)
        #   cancelled=False     → 아직 취소 안 됨
        #   paid 없음           → 결제 미완료
        #   company_name 없음   → 기업 고객 제외 (인보이스 처리)
        #   final_warning_at 없음 → 아직 최종 경고 안 보냄
        #   created <= cutoff   → 48시간 이상 무응답
        #   pickup_date > 임박선 → 픽업이 48시간 초과로 남음 (임박 건 제외)
        qs = Post.objects.filter(
            reminder=False,
            cash=False,
            cancelled=False,
            final_warning_at__isnull=True,
            created__lte=cutoff,
            pickup_date__gt=imminent_date,
        ).filter(
            Q(paid__isnull=True) | Q(paid='')
        ).filter(
            Q(company_name__isnull=True) | Q(company_name='')
        ).order_by('pickup_date', 'created')

        count = qs.count()
        label = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(f"\n{label}최종 경고 대상: {count}건 (무응답 {hours}시간 경과, 픽업 {IMMINENT_PICKUP_DAYS}일 초과)\n")

        sent = 0
        for notice in qs:
            self.stdout.write(
                f"  #{notice.id:<6} {str(notice.pickup_date)} {notice.pickup_time or '':<8} "
                f"{notice.name:<20} prepay={notice.prepay} arrival={_is_arrival(notice.direction)}"
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
                    "Final Reminder — Action Required",
                    "html_email-final-warning.html",
                    {
                        'booker_name': notice.booker_name,
                        'name': notice.name,
                        'pickup_date': notice.pickup_date,
                        'return_pickup_date': notice.return_pickup_date,
                        'price': notice.price,
                        'prepay': notice.prepay,
                        'is_arrival': _is_arrival(notice.direction),
                        'deadline': deadline,
                    },
                    recipients,
                )
                notice.final_warning_at = now
                notice.save(update_fields=['final_warning_at'])
                sent += 1
                logger.info(
                    'send_final_warning: warned Post pk=%s email=%s pickup_date=%s',
                    notice.pk, notice.email, notice.pickup_date,
                )
            except Exception as e:
                logger.error('send_final_warning: failed for Post pk=%s: %s', notice.pk, e)
                self.stdout.write(self.style.ERROR(f"Failed for #{notice.id}: {e}"))

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n[DRY RUN] 실제 발송 없음. {count}건 대상 확인 완료.\n'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n완료: {sent}건 최종 경고 발송.\n'))
