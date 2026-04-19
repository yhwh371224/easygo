"""
Create Twilio Proxy sessions for tomorrow's airport arrivals (default).

Usage:
    python manage.py create_proxy_sessions               # 내일 날짜
    python manage.py create_proxy_sessions --date 2025-06-01

Cron example (매일 저녁 19:00 — 서버 시간대 확인 후 조정):
    0 19 * * * /path/to/venv/bin/python /path/to/manage.py create_proxy_sessions
"""

import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from blog.models import Post
from blog.twilio_proxy import create_proxy_session
from utils.calendar_sync import sync_to_calendar

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create Twilio Proxy sessions for airport arrivals on a given date (default: tomorrow)'

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

        self.stdout.write(f"[create_proxy_sessions] Target date: {target_date}")

        # proxy_session_sid가 없거나 빈 값인 트립 대상 (취소 제외, 드라이버 미배정 제외)
        bookings = Post.objects.filter(
            pickup_date=target_date,
            cancelled=False,
            driver__isnull=False,
        ).filter(
            Q(proxy_session_sid='') | Q(proxy_session_sid__isnull=True)
        ).select_related('driver')

        if not bookings.exists():
            self.stdout.write("No eligible bookings found.")
            return

        success = 0
        fail = 0
        for booking in bookings:
            ok = create_proxy_session(booking)
            if ok:
                success += 1
                self.stdout.write(f"  OK   Post {booking.id} | {booking.name} | {booking.pickup_time}")
                # .update()는 시그널을 bypass하므로 드라이버 캘린더에 프록시 번호를 반영하기 위해 직접 동기화
                booking.refresh_from_db()
                if booking.driver and getattr(booking.driver, 'google_calendar_id', None):
                    sync_to_calendar(booking, calendar_id=booking.driver.google_calendar_id, is_driver=True)
            else:
                fail += 1
                self.stdout.write(f"  FAIL Post {booking.id} | {booking.name} | {booking.pickup_time}")

        self.stdout.write(f"\nDone. Success: {success}, Failed: {fail}")
