from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.bird_proxy import close_bird_mapping
from blog.sms_utils import normalize_phone  # ✔ FIX: single source of truth
from blog.models import Post


class Command(BaseCommand):
    help = 'Close Bird phone mapping for one specific driver trip'

    def add_arguments(self, parser):
        parser.add_argument('--driver', required=True, help='Driver name (partial match)')
        parser.add_argument('--trip', type=int, default=None, help='Trip number (1-based)')
        parser.add_argument('--date', type=str, default=None, help='0=today (default), 1=tomorrow, or YYYY-MM-DD')

    def handle(self, *args, **options):

        # =========================
        # DATE HANDLING
        # =========================
        raw_date = options['date']

        if raw_date is None or raw_date == '0':
            target_date = timezone.localdate()
        elif raw_date == '1':
            target_date = timezone.localdate() + timedelta(days=1)
        else:
            try:
                target_date = date.fromisoformat(raw_date)
            except ValueError:
                self.stderr.write(f"Invalid date format: {raw_date}")
                return

        driver_query = options['driver']
        trip_num = options['trip']

        # =========================
        # QUERY
        # =========================
        trips_list = list(
            Post.objects.filter(
                pickup_date=target_date,
                driver__driver_name__icontains=driver_query,
                driver__isnull=False,
                cancelled=False,
                use_proxy=True,
            )
            .select_related('driver')
            .order_by('pickup_time')
        )

        if not trips_list:
            self.stdout.write(
                f'No trips found for "{driver_query}" on {target_date}.'
            )
            return

        # =========================
        # LIST MODE
        # =========================
        if trip_num is None:
            self.stdout.write(
                f'Trips for "{driver_query}" on {target_date}:'
            )

            for i, trip in enumerate(trips_list, start=1):
                customer_phone = normalize_phone(trip.contact) or trip.contact or 'N/A'

                self.stdout.write(
                    f'  {i}. {trip.pickup_time} - '
                    f'{trip.name or "N/A"} ({customer_phone})'
                )
            return

        # =========================
        # VALIDATION
        # =========================
        if trip_num < 1 or trip_num > len(trips_list):
            self.stderr.write(
                f'Trip {trip_num} out of range (1–{len(trips_list)})'
            )
            return

        # =========================
        # SELECT TRIP
        # =========================
        booking = trips_list[trip_num - 1]
        driver = booking.driver
        driver_phone = driver.driver_contact

        customer_phone = normalize_phone(booking.contact)

        # =========================
        # OUTPUT
        # =========================
        self.stdout.write(
            f'Closing mapping: '
            f'{booking.pickup_time} | '
            f'{booking.name or "N/A"} ({customer_phone or booking.contact}) ↔ '
            f'{driver.driver_name} ({driver_phone})'
        )

        # =========================
        # EXECUTE
        # =========================
        ok = close_bird_mapping(booking)

        if ok:
            self.stdout.write('Done. use_proxy=False updated.')
        else:
            self.stderr.write('Failed.')