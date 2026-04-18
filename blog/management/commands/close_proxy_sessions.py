"""
Close Twilio Proxy sessions for today's completed airport arrivals (default).

Usage:
    python manage.py close_proxy_sessions                # 오늘 날짜
    python manage.py close_proxy_sessions --date 2025-06-01

Cron example (매일 자정):
    0 0 * * * /path/to/venv/bin/python /path/to/manage.py close_proxy_sessions
"""

import logging
from datetime import date

from django.core.management.base import BaseCommand
from blog.models import Post
from blog.twilio_proxy import close_proxy_session

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Close Twilio Proxy sessions for airport arrivals on a given date (default: today)'

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
            target_date = date.today()

        self.stdout.write(f"[close_proxy_sessions] Target date: {target_date}")

        bookings = Post.objects.filter(
            pickup_date=target_date,
            direction__icontains='Pickup from',
        ).exclude(
            proxy_session_sid__isnull=True,
        ).exclude(
            proxy_session_sid='',
        )

        if not bookings.exists():
            self.stdout.write("No active proxy sessions found for this date.")
            return

        success = 0
        fail = 0
        for booking in bookings:
            ok = close_proxy_session(booking)
            if ok:
                success += 1
                self.stdout.write(f"  OK  Post {booking.id} | {booking.name} | {booking.pickup_time}")
            else:
                fail += 1
                self.stdout.write(f"  FAIL Post {booking.id} | {booking.name} | {booking.pickup_time}")

        self.stdout.write(f"\nDone. Success: {success}, Failed: {fail}")
