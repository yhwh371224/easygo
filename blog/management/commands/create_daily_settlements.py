import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Driver, Post
from blog.services.settlement_service import SettlementService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        '당일 정산 드라이버(settle_daily=True, is_company=False, is_active=True)의 '
        '당일 예약을 자동으로 정산 처리 (same-day settlement). 협력업체'
        '(is_company=True)나 주/월 단위로 모아서 정산하는 드라이버'
        '(settle_daily=False)는 관리자가 수동으로 정산한다.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='YYYY-MM-DD (default: today)',
        )

    def handle(self, *args, **options):

        # =========================
        # DATE RESOLVE
        # =========================
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stderr.write(f"Invalid date format: {options['date']}")
                return
        else:
            target_date = timezone.localdate()

        logger.info('[create_daily_settlements] Start date=%s', target_date)

        # =========================
        # QUERY
        # =========================
        # settle_daily=False 는 주/월 단위로 모아서 정산받는 드라이버 — 여기서
        # 정산서를 만들어 버리면 실제로 지급하지 않은 돈이 '정산 완료'로 잡히고,
        # 그 트립이 드라이버 대시보드의 받을 돈에서 사라진다.
        driver_ids = Post.objects.filter(
            pickup_date=target_date,
            cancelled=False,
            driver__isnull=False,
            driver__is_company=False,
            driver__is_active=True,
            driver__settle_daily=True,
        ).values_list('driver_id', flat=True).distinct()

        drivers = list(Driver.objects.filter(id__in=driver_ids))

        if not drivers:
            logger.info('[create_daily_settlements] No eligible drivers')
            return

        success = 0
        skipped = 0
        fail = 0

        # =========================
        # PROCESS
        # =========================
        for driver in drivers:
            try:
                settlement = SettlementService.create_settlement(
                    driver, target_date, target_date, user=None,
                )

                if settlement is None:
                    skipped += 1
                    logger.info(
                        '[SETTLE SKIP] driver=%s date=%s - no unsettled trips',
                        driver, target_date,
                    )
                else:
                    success += 1
                    logger.info(
                        '[SETTLE OK] driver=%s settlement=%s paid_total=%s',
                        driver, settlement.settlement_number, settlement.paid_total,
                    )

            except Exception as e:
                fail += 1
                logger.error(
                    '[SETTLE ERROR] driver=%s error=%s', driver, str(e),
                )

        # =========================
        # SUMMARY
        # =========================
        logger.info(
            '[create_daily_settlements DONE] success=%s skipped=%s fail=%s',
            success, skipped, fail,
        )

        self.stdout.write(
            f'Done. Settled: {success}, Skipped: {skipped}, Failed: {fail}'
        )
