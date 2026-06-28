import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from blog.models import Post

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '컨펌 이메일 발송 후 48시간 내 응답 없는 pending 부킹 자동 취소'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 취소 없이 대상 목록만 출력',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=48,
            help='기준 시간 (기본값: 48시간)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours = options['hours']
        cutoff = timezone.now() - timedelta(hours=hours)

        # 이메일 경고 문구가 발송된 조건과 동일:
        #   sent_email=True  → 컨펌 이메일 발송됨
        #   reminder=False   → 아직 응답 없음
        #   paid 없음        → 결제 미완료
        #   cash=False       → 캐쉬 미선택 (선택했으면 이미 확정)
        #   company_name 없음 → 기업 고객 제외 (인보이스 처리)
        #   cancelled=False  → 아직 취소 안 됨
        #   created <= cutoff → 48시간 이상 경과
        qs = Post.objects.filter(
            sent_email=True,
            reminder=False,
            cancelled=False,
            cash=False,
            created__lte=cutoff,
        ).filter(
            Q(paid__isnull=True) | Q(paid='')
        ).filter(
            Q(company_name__isnull=True) | Q(company_name='')
        ).order_by('pickup_date', 'created')

        count = qs.count()
        label = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(f"\n{label}자동 취소 대상: {count}건 (기준: 생성 후 {hours}시간 경과)\n")

        for post in qs:
            self.stdout.write(
                f"  #{post.id:<6} {str(post.pickup_date)} {post.pickup_time or '':<8} "
                f"{post.name:<20} prepay={post.prepay} pending={post.pending}"
            )
            if not dry_run:
                post.cancelled = True
                # update_fields 지정 → post_save 시그널 → create_event_on_calendar 태스크 → 캘린더 업데이트
                post.save(update_fields=['cancelled'])
                logger.info(
                    'auto_cancel_pending: cancelled Post pk=%s email=%s pickup_date=%s',
                    post.pk, post.email, post.pickup_date,
                )

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n[DRY RUN] 실제 취소 없음. {count}건 대상 확인 완료.\n'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n완료: {count}건 자동 취소 및 캘린더 업데이트 요청.\n'))
