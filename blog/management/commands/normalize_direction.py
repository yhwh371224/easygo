from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from blog.models import Post
from utils.direction_utils import (
    INTL_AIRPORT, DOMESTIC_AIRPORT,
    is_intl_pickup, is_domestic_pickup,
)

CANONICAL = {
    True: INTL_AIRPORT,
    False: DOMESTIC_AIRPORT,
}


def canonical_value(value):
    """Return the canonical direction string, or None if not an airport pickup."""
    if is_intl_pickup(value):
        return INTL_AIRPORT
    if is_domestic_pickup(value):
        return DOMESTIC_AIRPORT
    return None


class Command(BaseCommand):
    help = (
        'Find Post records where direction/return_direction is a misspelled airport '
        'pickup string and optionally fix them. Dry-run by default.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually update the DB. Without this flag the command only reports.',
        )

    def handle(self, *args, **options):
        fix = options['fix']

        since = timezone.now() - timedelta(days=2)

        # Fetch records created in the last 2 days where either field loosely contains 'pickup'
        candidates = Post.objects.filter(
            created__gte=since,
        ).filter(
            Q(direction__icontains='pickup') | Q(return_direction__icontains='pickup')
        ).only('id', 'name', 'email', 'pickup_date', 'direction', 'return_direction')

        to_fix = []

        for post in candidates:
            changes = {}

            canonical_dir = canonical_value(post.direction)
            if canonical_dir and post.direction != canonical_dir:
                changes['direction'] = (post.direction, canonical_dir)

            canonical_ret = canonical_value(post.return_direction)
            if canonical_ret and post.return_direction != canonical_ret:
                changes['return_direction'] = (post.return_direction, canonical_ret)

            if changes:
                to_fix.append((post, changes))

        if not to_fix:
            self.stdout.write(self.style.SUCCESS('No direction mismatches found.'))
            return

        self.stdout.write(
            self.style.WARNING(f'Found {len(to_fix)} record(s) with non-canonical direction values:\n')
        )

        for post, changes in to_fix:
            self.stdout.write(
                f'  id={post.id}  {post.name or ""}  {post.email or ""}  {post.pickup_date}'
            )
            for field, (old_val, new_val) in changes.items():
                self.stdout.write(f'    {field}: {old_val!r}  →  {new_val!r}')

        if not fix:
            self.stdout.write(
                self.style.WARNING('\nDry-run complete. Run with --fix to apply changes.')
            )
            return

        # Apply fixes
        updated = 0
        for post, changes in to_fix:
            for field, (_, new_val) in changes.items():
                setattr(post, field, new_val)
            Post.objects.filter(pk=post.pk).update(
                **{field: new_val for field, (_, new_val) in changes.items()}
            )
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'\nFixed {updated} record(s).'))
