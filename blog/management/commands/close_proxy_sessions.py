"""
Close Bird phone mappings for today's completed airport arrivals (default).

Usage:
    python manage.py close_proxy_sessions                # 오늘 날짜
    python manage.py close_proxy_sessions --date 2025-06-01

Cron example (매일 자정):
    0 0 * * * /path/to/venv/bin/python /path/to/manage.py close_proxy_sessions
"""

import logging
from datetime import date, datetime, timedelta

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
            help='Target pickup date in YYYY-MM-DD format (default: today)',
        )

    def handle(self, *args, **options):
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stderr.write(f"Invalid date format: {options['date']}. Use YYYY-MM-DD.")
                return
        else:
            target_date = timezone.localdate()

        self.stdout.write(f'[close_proxy_sessions] Target date: {target_date}')

        bookings = Post.objects.filter(
            pickup_date=target_date,
            direction__icontains='Pickup from',
            driver__isnull=False,
        ).select_related('driver')

        if not bookings.exists():
            self.stdout.write('No bookings found for this date.')
            return

        now = timezone.localtime()
        success = 0
        fail = 0
        skipped = 0
        for booking in bookings:
            try:
                pickup_naive = datetime.strptime(booking.pickup_time, '%H:%M').replace(
                    year=target_date.year, month=target_date.month, day=target_date.day
                )
                pickup_dt = timezone.make_aware(pickup_naive)
            except (ValueError, TypeError):
                logger.warning('Post %s: pickup_time 파싱 실패 (%r) — 스킵', booking.id, booking.pickup_time)
                skipped += 1
                continue

            if pickup_dt + timedelta(hours=1) > now:
                continue

            ok = close_bird_mapping(booking)
            if ok:
                success += 1
                self.stdout.write(f'  OK  Post {booking.id} | {booking.name} | {booking.pickup_time}')
            else:
                fail += 1
                self.stdout.write(f'  FAIL Post {booking.id} | {booking.name} | {booking.pickup_time}')

        self.stdout.write(f'\nDone. Success: {success}, Failed: {fail}, Skipped (parse error): {skipped}')
