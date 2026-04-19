"""
Create Bird phone mappings for tomorrow's airport arrivals (default).

Usage:
    python manage.py create_proxy_sessions               # 내일 날짜
    python manage.py create_proxy_sessions --date 2025-06-01

Cron example (매일 저녁 19:00 — 서버 시간대 확인 후 조정):
    0 19 * * * /path/to/venv/bin/python /path/to/manage.py create_proxy_sessions
"""

import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from blog.models import Post
from blog.bird_proxy import create_bird_mapping
from utils.calendar_sync import sync_to_calendar

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create Bird phone mappings for airport arrivals on a given date (default: tomorrow)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Target pickup date in YYYY-MM-DD format (default: tomorrow)',
        )

    def handle(self, *args, **options):
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stderr.write(f"Invalid date format: {options['date']}. Use YYYY-MM-DD.")
                return
        else:
            target_date = date.today() + timedelta(days=1)

        self.stdout.write(f'[create_proxy_sessions] Target date: {target_date}')

        bookings = Post.objects.filter(
            pickup_date=target_date,
            cancelled=False,
            driver__isnull=False,
            use_proxy=True,
        ).select_related('driver')

        if not bookings.exists():
            self.stdout.write('No eligible bookings found.')
            return

        success = 0
        fail = 0
        for booking in bookings:
            ok = create_bird_mapping(booking)
            if ok:
                success += 1
                self.stdout.write(f'  OK   Post {booking.id} | {booking.name} | {booking.pickup_time}')
                if booking.driver and getattr(booking.driver, 'google_calendar_id', None):
                    sync_to_calendar(booking, calendar_id=booking.driver.google_calendar_id, is_driver=True)
            else:
                fail += 1
                self.stdout.write(f'  FAIL Post {booking.id} | {booking.name} | {booking.pickup_time}')

        self.stdout.write(f'\nDone. Success: {success}, Failed: {fail}')
