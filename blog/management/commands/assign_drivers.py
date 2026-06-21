import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Post
from blog.blog_utils import resolve_driver, get_default_driver_for_region
from regions.models import Region
from utils.direction_utils import is_airport_pickup

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Assign drivers to unassigned airport-pickup bookings from today onwards."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be assigned without saving.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.localdate()

        sydney_region = Region.objects.filter(slug='sydney', is_active=True).first()

        posts = Post.objects.filter(
            pickup_date__gte=today,
            driver__isnull=True,
            cancelled=False,
        ).select_related('region')

        # 공항 픽업(도착 비행기)인 것만
        posts = [p for p in posts if is_airport_pickup(p.direction)]

        if not posts:
            self.stdout.write("No unassigned airport-pickup bookings found.")
            return

        assigned = 0
        skipped = 0

        for post in posts:
            driver = resolve_driver(post.suburb)

            if not driver:
                driver = get_default_driver_for_region(post.region)

            if not driver and sydney_region:
                driver = get_default_driver_for_region(sydney_region)

            if not driver:
                logger.warning(
                    "assign_drivers: no driver found for Post pk=%s suburb=%s region=%s",
                    post.pk, post.suburb, post.region,
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP  pk={post.pk} {post.name} {post.pickup_date} "
                        f"suburb={post.suburb} region={post.region}"
                    )
                )
                skipped += 1
                continue

            self.stdout.write(
                f"  {'[DRY]' if dry_run else 'ASSIGN'} "
                f"pk={post.pk} {post.name} {post.pickup_date} "
                f"→ {driver.driver_name}"
            )

            if not dry_run:
                post.driver = driver
                post.save(update_fields=['driver'])
                logger.info(
                    "assign_drivers: assigned driver=%s to Post pk=%s",
                    driver.pk, post.pk,
                )
            assigned += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. assigned={assigned} skipped={skipped}"
                + (" (dry run — nothing saved)" if dry_run else "")
            )
        )
