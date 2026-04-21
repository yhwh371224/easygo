"""
Close a single Bird phone mapping for one specific driver trip.

Usage:
    python manage.py close_one_proxy_session --driver Sam
    python manage.py close_one_proxy_session --driver Sam --trip 1
    python manage.py close_one_proxy_session --driver Sam --trip 2 --date 2026-04-20
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.bird_proxy import _format_e164
from blog.models import PhoneMapping, Post


class Command(BaseCommand):
    help = 'Close Bird phone mapping for one specific driver trip'

    def add_arguments(self, parser):
        parser.add_argument('--driver', required=True, help='Driver name (partial match)')
        parser.add_argument('--trip', type=int, default=None, help='Trip number (1-based, pickup_time order)')
        parser.add_argument('--date', type=str, default=None, help='Date in YYYY-MM-DD format (default: today)')

    def handle(self, *args, **options):
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stderr.write(f"Invalid date format: {options['date']}. Use YYYY-MM-DD.")
                return
        else:
            target_date = timezone.localdate()

        driver_query = options['driver']
        trip_num = options['trip']

        trips_list = list(
            Post.objects.filter(
                pickup_date=target_date,
                driver__driver_name__icontains=driver_query,
                cancelled=False,
                use_proxy=True,
            )
            .select_related('driver')
            .order_by('pickup_time')
        )

        if not trips_list:
            self.stdout.write(f'No trips found for driver "{driver_query}" on {target_date}.')
            return

        if trip_num is None:
            self.stdout.write(f'Trips for driver matching "{driver_query}" on {target_date}:')
            for i, trip in enumerate(trips_list, start=1):
                customer_phone = _format_e164(trip.contact) or trip.contact or 'N/A'
                self.stdout.write(f'  {i}. {trip.pickup_time} - 손님: {trip.name} ({customer_phone})')
            return
        if trip_num < 1 or trip_num > len(trips_list):
            self.stderr.write(f'Trip number {trip_num} is out of range (1–{len(trips_list)}).')
            return

        booking = trips_list[trip_num - 1]
        driver = booking.driver
        customer_phone = _format_e164(booking.contact)
        driver_phone = _format_e164(driver.driver_contact if driver else None)

        self.stdout.write(
            f'Closing mapping for trip {trip_num}: '
            f'{booking.pickup_time} | {booking.name} ({customer_phone}) ↔ '
            f'{driver.driver_name if driver else "N/A"} ({driver_phone})'
        )

        if not driver_phone:
            self.stderr.write(f'경고: 드라이버 번호 없음 ({driver.driver_name if driver else "N/A"})')

        numbers = [n for n in [customer_phone, driver_phone] if n]
        if not numbers:
            self.stderr.write('No valid phone numbers found — nothing to delete.')
            return

        deleted, _ = PhoneMapping.objects.filter(from_number__in=numbers).delete()
        if deleted > 0:
            Post.objects.filter(pk=booking.pk).update(use_proxy=False)
            self.stdout.write(f'Done. {deleted} mapping(s) deleted. use_proxy=False 설정됨.')
        else:
            self.stdout.write('매핑이 없습니다. use_proxy 변경 안 함.')
