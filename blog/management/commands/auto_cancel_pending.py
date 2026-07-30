import logging

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from blog.models import Post
from blog import dunning
from blog.blog_utils import booking_balance, is_deposit_protected
from utils.post_helper import send_post_cancelled_email

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Final notice 발송 후 유예가 지난 미결제/부분결제 부킹을 자동 취소 + 취소 통보.\n'
        '취소 시점 = max(픽업 컷오프[dep 24h/arr 48h 전], 예약시각 + 12h). '
        '취소 예고 메일(미결제=final_notice, 부분결제=discrepancy_final)을 실제로 '
        '보낸 건만(경고 없이 취소하지 않음).'
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
        #   cash=False           → 캐쉬 미선택
        #   cancelled=False      → 아직 취소 안 됨
        #   company_name 없음    → 기업 고객 제외 (인보이스 처리)
        #   취소 예고 메일을 실제로 보낸 건만 (미결제=final_notice_sent_at,
        #   부분결제=discrepancy_final_sent_at)
        #  ※ reminder 는 조건이 아님 — "곧 낼게요" 응답만 하고 미결제인 건도 취소 대상.
        #  ※ 금액(paid) 조건은 DB 에서 못 건다(CharField + surcharge/discount 반영
        #    필요) → 2차 Python 필터에서 booking_balance 로 판정.
        qs = Post.objects.filter(
            cancelled=False,
            cash=False,
        ).filter(
            Q(final_notice_sent_at__isnull=False)
            | Q(discrepancy_final_sent_at__isnull=False)
        ).filter(
            Q(company_name__isnull=True) | Q(company_name='')
        ).order_by('pickup_date', 'created')

        # 2차 필터(Python): 미납 여부 + 컷오프 공식 도달 여부.
        targets = [p for p in qs if self._is_target(p, now)]

        count = len(targets)
        label = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(f"\n{label}자동 취소 대상: {count}건\n")

        cancelled = 0
        for post in targets:
            deadline = dunning.cancel_deadline(post)
            # _is_target 을 통과한 건이므로 None 이 아니지만 방어적으로 언팩.
            _, paid, balance = booking_balance(post) or (0.0, 0.0, 0.0)
            notified_at = (
                post.discrepancy_final_sent_at if paid > 0 else post.final_notice_sent_at
            )
            self.stdout.write(
                f"  #{post.id:<6} {str(post.pickup_date)} {post.pickup_time or '':<8} "
                f"{post.name:<20} arrival={dunning.is_airport_arrival(post)} "
                f"deadline={deadline:%Y-%m-%d %H:%M} "
                f"notice={notified_at:%Y-%m-%d %H:%M} "
                f"paid=${paid:.2f} balance=${balance:.2f}"
            )
            if dry_run:
                continue

            # 1️⃣ 취소 통보 메일 (먼저 보내 실패 시 취소 전 중단)
            #    부분결제 건은 이미 낸 금액/미납 잔액을 메일에 명시한다.
            try:
                if paid > 0:
                    send_post_cancelled_email(
                        post,
                        unpaid_balance=f"{balance:.2f}",
                        amount_paid=f"{paid:.2f}",
                    )
                else:
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
                'auto_cancel_pending: cancelled Post pk=%s email=%s pickup_date=%s '
                'paid=%.2f balance=%.2f',
                post.pk, post.email, post.pickup_date, paid, balance,
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n[DRY RUN] 실제 취소 없음. {count}건 대상 확인 완료.\n'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n완료: {cancelled}건 자동 취소 및 취소 통보 발송.\n'))

    def _is_target(self, post, now):
        """이 부킹이 지금 자동취소 대상인지.

        미결제(paid 0/공백)  : final_notice_sent_at 이 예고 시각.
                              (금액을 못 뽑는 건도 기존과 동일하게 미결제로 본다)
        부분결제(paid > 0)   : 잔액이 남아 있고(디파짓 충족분 제외),
                              discrepancy_final_sent_at 이 예고 시각.

        공통: 예고 메일을 실제로 보냈고 + 그로부터 GRACE_HOURS 지났고 + 픽업 컷오프 도달.
        """
        amounts = booking_balance(post)
        if amounts is None:
            # price/paid 가 비숫자 텍스트 → 미납인지 알 수 없음. 취소하지 않는다.
            logger.warning(
                'auto_cancel_pending: skipped Post pk=%s — non-numeric price=%r paid=%r',
                post.pk, post.price, post.paid,
            )
            return False
        _, paid, balance = amounts

        if paid <= 0:
            notified_at = post.final_notice_sent_at
        else:
            # 완납/과납이면 대상 아님 — 예고 메일을 받은 뒤 잔액을 낸 손님 보호.
            if balance <= 0:
                return False
            # 디파짓 건은 분할 결제 중이라 보호되지만, 잔액 안내를 두 번 받고도
            # 픽업이 임박해 취소 예고까지 나갔으면 보호가 풀린다(무기한 대기 방지).
            if is_deposit_protected(post):
                return False
            notified_at = post.discrepancy_final_sent_at

        # 경고 없이 취소하지 않는다.
        if notified_at is None:
            return False

        # 예고 후 GRACE_HOURS 를 실제 발송 시각 기준으로 보장한다.
        #
        # 사다리 단계(픽업 -48h/-72h)와 취소 컷오프(픽업 -24h/-48h) 사이 간격이
        # 24h 라 "크론이 촘촘히 돌면" 자동으로 만족되지만, 크론이 하루 1회면
        # 예고가 컷오프 직전에 나가 유예가 15h 남짓으로 쪼그라든다. 그러면 메일에
        # 쓴 "24시간 내 미결제 시 취소" 약속을 시스템이 어기게 된다.
        # → 스케줄 간격과 무관하게 코드에서 보장한다.
        # (유예가 픽업을 넘기면 is_cancel_eligible 이 False → 수동 처리 영역)
        if now < notified_at + timedelta(hours=dunning.GRACE_HOURS):
            return False

        return dunning.is_cancel_eligible(post, now)
