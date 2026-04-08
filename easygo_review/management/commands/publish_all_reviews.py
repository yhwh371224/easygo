from django.core.management.base import BaseCommand

from easygo_review.models import Post


class Command(BaseCommand):
    help = "One-time: set is_published=True for all unpublished reviews."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Show how many would be updated without making changes.",
        )

    def handle(self, *args, **options):
        qs = Post.objects.filter(is_published=False)
        count = qs.count()

        if count == 0:
            self.stdout.write("No unpublished reviews found.")
            return

        if options['dry_run']:
            self.stdout.write(f"[dry-run] {count} review(s) would be published:")
            for post in qs:
                self.stdout.write(f"  pk={post.pk} | {post.name} | rating={post.rating}")
            return

        updated = qs.update(is_published=True)
        self.stdout.write(self.style.SUCCESS(f"Published {updated} review(s)."))
