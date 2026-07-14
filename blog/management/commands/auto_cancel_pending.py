import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from blog.models import Post
from utils.post_helper import send_post_cancelled_email

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '최종 경고(final_warning) 발송 후 유예 시간 내 응답 없는 부킹 자동 취소 + 취소 통보 메일'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 취소 없이 대상 목록만 출력',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='최종 경고 후 유예 시간 (기본값: 24시간)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours = options['hours']
        cutoff = timezone.now() - timedelta(hours=hours)

        # 자동 취소 대상 (send_final_warning 이후 유예 경과 건):
        #   final_warning_at 존재       → 최종 경고를 이미 보냄
        #   final_warning_at <= cutoff  → 유예 시간(기본 24h) 경과
        #   reminder=False              → 여전히 응답 없음
        #   cash=False                  → 캐쉬 미선택 (선택했으면 확정)
        #   paid 없음                   → 결제 미완료
        #   company_name 없음           → 기업 고객 제외 (인보이스 처리)
        #   cancelled=False             → 아직 취소 안 됨
        qs = Post.objects.filter(
            final_warning_at__isnull=False,
            final_warning_at__lte=cutoff,
            reminder=False,
            cancelled=False,
            cash=False,
        ).filter(
            Q(paid__isnull=True) | Q(paid='')
        ).filter(
            Q(company_name__isnull=True) | Q(company_name='')
        ).order_by('pickup_date', 'created')

        count = qs.count()
        label = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(f"\n{label}자동 취소 대상: {count}건 (최종 경고 후 {hours}시간 경과)\n")

        cancelled = 0
        for post in qs:
            self.stdout.write(
                f"  #{post.id:<6} {str(post.pickup_date)} {post.pickup_time or '':<8} "
                f"{post.name:<20} prepay={post.prepay} warned={post.final_warning_at:%Y-%m-%d %H:%M}"
            )
            if dry_run:
                continue

            # 1️⃣ 취소 통보 메일 (먼저 보내 실패 시 취소 전 중단)
            try:
                send_post_cancelled_email(post)
            except Exception as e:
                logger.error('auto_cancel_pending: cancel email failed for Post pk=%s: %s — skipping cancel', post.pk, e)
                self.stdout.write(self.style.ERROR(f"Cancel email failed for #{post.id}: {e} — skipped"))
                continue

            # 2️⃣ 취소 처리
            post.cancelled = True
            # update_fields 지정 → post_save 시그널 → create_event_on_calendar 태스크 → 캘린더 업데이트
            post.save(update_fields=['cancelled'])
            cancelled += 1
            logger.info(
                'auto_cancel_pending: cancelled Post pk=%s email=%s pickup_date=%s',
                post.pk, post.email, post.pickup_date,
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n[DRY RUN] 실제 취소 없음. {count}건 대상 확인 완료.\n'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n완료: {cancelled}건 자동 취소 및 취소 통보 발송.\n'))
