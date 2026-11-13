from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from easygo_review.models import GoogleRatingSnapshot
from easygo_review.review_stats import (
    clear_review_stats_cache, fetch_google_rating, find_place_ids,
)


class Command(BaseCommand):
    help = ("Fetch the Google Business Profile rating + review count (weekly cron). "
            "--find prints candidate place IDs for GOOGLE_PLACE_ID.")

    def add_arguments(self, parser):
        parser.add_argument('--find', metavar='QUERY', nargs='?', const='EasyGo Airport Shuttle',
                            help='Search places and print their IDs instead of refreshing.')

    def handle(self, *args, **options):
        if options['find']:
            if not settings.GOOGLE_PLACES_API_KEY:
                raise CommandError('GOOGLE_PLACES_API_KEY is not set')
            for pid, name, addr, rating, count in find_place_ids(options['find']):
                self.stdout.write(f"{pid}  {name}  {rating} ({count})  {addr}")
            return

        if not settings.GOOGLE_PLACES_API_KEY or not settings.GOOGLE_PLACE_ID:
            # Not configured yet: keep the saved/fallback numbers, no cron alert.
            self.stdout.write(self.style.WARNING(
                'GOOGLE_PLACES_API_KEY / GOOGLE_PLACE_ID not set — skipped (site keeps last numbers)'))
            return

        try:
            rating, count = fetch_google_rating(settings.GOOGLE_PLACE_ID)
        except Exception as exc:
            # Non-zero exit → cronwrap.sh sends the Telegram alert; the site keeps
            # showing the last saved numbers.
            raise CommandError(f'Google rating fetch failed: {exc}')

        prev = GoogleRatingSnapshot.objects.first()
        GoogleRatingSnapshot.objects.create(rating=Decimal(str(round(rating, 1))), review_count=count)
        clear_review_stats_cache()
        was = f" (was {prev.rating} / {prev.review_count})" if prev else ''
        self.stdout.write(self.style.SUCCESS(f'Google rating {rating:.1f} / {count} reviews{was}'))
