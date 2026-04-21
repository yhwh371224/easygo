import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Post
from blog.bird_proxy import close_bird_mapping

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Close Bird phone mappings for airport arrivals on a given date (default: today)'

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

        logger.info('[close_proxy_sessions] Start date=%s', target_date)

        # =========================
        # QUERY
        # =========================
        bookings = list(Post.objects.filter(
            pickup_date=target_date,
            cancelled=False,
            use_proxy=True,
            driver__isnull=False,
        ).select_related('driver'))

        if not bookings:
            logger.info('[close_proxy_sessions] No bookings found')
            return

        success = 0
        fail = 0

        # =========================
        # PROCESS
        # =========================
        for booking in bookings:
            try:
                ok = close_bird_mapping(booking)

                if ok:
                    success += 1
                    logger.info(
                        '[CLOSE OK] Post=%s name=%s time=%s',
                        booking.id,
                        booking.name,
                        booking.pickup_time,
                    )
                else:
                    fail += 1
                    logger.warning(
                        '[CLOSE FAIL] Post=%s name=%s',
                        booking.id,
                        booking.name,
                    )

            except Exception as e:
                fail += 1
                logger.error(
                    '[CLOSE ERROR] Post=%s error=%s',
                    booking.id,
                    str(e),
                )

        # =========================
        # SUMMARY
        # =========================
        logger.info(
            '[close_proxy_sessions DONE] success=%s fail=%s',
            success,
            fail,
        )

        self.stdout.write(
            f'Done. Success: {success}, Failed: {fail}'
        )