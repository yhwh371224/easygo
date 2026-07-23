import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Post
from blog.blog_utils import assign_default_driver_if_missing
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
            driver = assign_default_driver_if_missing(post, dry_run=dry_run)

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
            assigned += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. assigned={assigned} skipped={skipped}"
                + (" (dry run — nothing saved)" if dry_run else "")
            )
        )
