from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.bird_proxy import close_bird_mapping
from sms_utils import normalize_phone  # ✔ FIX: single source of truth
from blog.models import Post


class Command(BaseCommand):
    help = 'Close Bird phone mapping for one specific driver trip'

    def add_arguments(self, parser):
        parser.add_argument('--driver', required=True, help='Driver name (partial match)')
        parser.add_argument('--trip', type=int, default=None, help='Trip number (1-based)')
        parser.add_argument('--date', type=str, default=None, help='YYYY-MM-DD (default: today)')

    def handle(self, *args, **options):

        # =========================
        # DATE HANDLING
        # =========================
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stderr.write(f"Invalid date format: {options['date']}")
                return
        else:
            target_date = timezone.localdate()

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