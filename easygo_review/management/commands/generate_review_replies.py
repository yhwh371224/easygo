from django.core.management.base import BaseCommand
from django.db.models import Q

from easygo_review.models import Post
from easygo_review.tasks import generate_review_reply


class Command(BaseCommand):
    help = "Queue generate_review_reply tasks for all published reviews without a reply."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="List matching reviews without queuing tasks.",
        )

    def handle(self, *args, **options):
        qs = Post.objects.filter(is_published=True).filter(
            Q(reply__isnull=True) | Q(reply='')
        )

        count = qs.count()
        if count == 0:
            self.stdout.write("No published reviews without a reply.")
            return

        self.stdout.write(f"Found {count} review(s) without a reply.")

        if options['dry_run']:
            for post in qs:
                self.stdout.write(f"  [dry-run] pk={post.pk} | {post.name} | rating={post.rating}")
            return

        for post in qs:
            generate_review_reply.delay(post.pk)
            self.stdout.write(f"  Queued pk={post.pk} | {post.name} | rating={post.rating}")

        self.stdout.write(self.style.SUCCESS(f"Queued {count} task(s)."))
