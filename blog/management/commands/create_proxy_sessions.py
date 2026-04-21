import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Post
from blog.bird_proxy import create_bird_mapping
from utils.calendar_sync import sync_to_calendar

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create Bird phone mappings for use_proxy=True bookings (default: tomorrow)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='YYYY-MM-DD (default: tomorrow)',
        )

    def handle(self, *args, **options):

        # =========================
        # DATE RESOLVE
        # =========================
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stderr.write("Invalid date format")
                return
        else:
            target_date = timezone.localdate() + timedelta(days=1)

        logger.info('[create_proxy_sessions] Start date=%s', target_date)

        # =========================
        # QUERY
        # =========================
        bookings = list(
            Post.objects.filter(
                pickup_date=target_date,
                cancelled=False,
                driver__isnull=False,
                use_proxy=True,
            ).select_related('driver')
        )

        if not bookings:
            logger.info('No eligible bookings found.')
            return

        success = 0
        fail = 0

        # =========================
        # PROCESS
        # =========================
        for booking in bookings:

            try:
                ok = create_bird_mapping(booking)

                if not ok:
                    fail += 1
                    logger.warning(
                        '[CREATE FAIL] Post=%s name=%s reason=mapping_failed',
                        booking.id,
                        booking.name,
                    )
                    continue

                success += 1
                logger.info(
                    '[CREATE OK] Post=%s name=%s time=%s',
                    booking.id,
                    booking.name,
                    booking.pickup_time,
                )

                # =========================
                # Calendar sync (NON-BLOCKING)
                # =========================
                try:
                    if booking.driver.google_calendar_id:
                        sync_to_calendar(
                            booking,
                            calendar_id=booking.driver.google_calendar_id,
                            is_driver=True,
                        )
                except Exception as e:
                    logger.warning(
                        '[CALENDAR WARN] Post=%s error=%s',
                        booking.id,
                        str(e),
                    )

            except Exception as e:
                fail += 1
                logger.error(
                    '[CREATE ERROR] Post=%s error=%s',
                    booking.id,
                    str(e),
                )

        # =========================
        # SUMMARY
        # =========================
        logger.info(
            '[create_proxy_sessions DONE] success=%s fail=%s',
            success,
            fail,
        )

        self.stdout.write(f'Done. Success: {success}, Failed: {fail}')