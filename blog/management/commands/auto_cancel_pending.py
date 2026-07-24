import logging

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from blog.models import Post
from blog import dunning
from utils.post_helper import send_post_cancelled_email

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Final notice 발송 후 유예가 지난 미결제 부킹을 자동 취소 + 취소 통보.\n'
        '취소 시점 = max(픽업 컷오프[dep 24h/arr 48h 전], 예약시각 + 12h). '
        'final notice 를 실제로 보낸 건만(경고 없이 취소하지 않음).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='실제 취소 없이 대상 목록만 출력',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()

        # 1차 필터(DB): 자동취소 후보군.
        #   paid 없음            → 결제 미완료
        #   cash=False           → 캐쉬 미선택
        #   cancelled=False      → 아직 취소 안 됨
        #   company_name 없음    → 기업 고객 제외 (인보이스 처리)
        #   final_notice_sent_at → Final notice(자동취소 예고)를 실제로 보낸 건만
        #  ※ reminder 는 더 이상 조건이 아님 — "곧 낼게요" 응답만 하고 미결제인 건도 취소 대상.
        qs = Post.objects.filter(
            cancelled=False,
            cash=False,
            final_notice_sent_at__isnull=False,
        ).filter(
            Q(paid__isnull=True) | Q(paid='')
        ).filter(
            Q(company_name__isnull=True) | Q(company_name='')
        ).order_by('pickup_date', 'created')

        # 2차 필터(Python): 컷오프 공식 — max(픽업 컷오프, 예약시각+12h) 도달했는지.
        #   (유예가 픽업을 넘어가는 초임박 건은 is_cancel_eligible 이 False → 제외)
        targets = [p for p in qs if dunning.is_cancel_eligible(p, now)]

        count = len(targets)
        label = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(f"\n{label}자동 취소 대상: {count}건\n")

        cancelled = 0
        for post in targets:
            deadline = dunning.cancel_deadline(post)
            self.stdout.write(
                f"  #{post.id:<6} {str(post.pickup_date)} {post.pickup_time or '':<8} "
                f"{post.name:<20} arrival={dunning.is_airport_arrival(post)} "
                f"deadline={deadline:%Y-%m-%d %H:%M} "
                f"final_notice={post.final_notice_sent_at:%Y-%m-%d %H:%M}"
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
            # update_fields 지정 → post_save 시그널 → 캘린더 업데이트
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
