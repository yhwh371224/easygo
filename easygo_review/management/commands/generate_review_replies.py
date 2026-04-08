from django.core.management.base import BaseCommand

from easygo_review.models import Comment, Post
from easygo_review.tasks import EASYGO_AUTHOR, generate_review_reply


class Command(BaseCommand):
    help = "Queue generate_review_reply tasks for all reviews without an EasyGo reply comment."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="List matching reviews without queuing tasks.",
        )

    def handle(self, *args, **options):
        replied_ids = Comment.objects.filter(author=EASYGO_AUTHOR).values_list('post_id', flat=True)
        qs = Post.objects.exclude(pk__in=replied_ids)

        count = qs.count()
        if count == 0:
            self.stdout.write("No reviews without an EasyGo reply.")
            return

        self.stdout.write(f"Found {count} review(s) without an EasyGo reply.")

        if options['dry_run']:
            for post in qs:
                self.stdout.write(f"  [dry-run] pk={post.pk} | {post.name} | rating={post.rating}")
            return

        for post in qs:
            generate_review_reply.delay(post.pk)
            self.stdout.write(f"  Queued pk={post.pk} | {post.name} | rating={post.rating}")

        self.stdout.write(self.style.SUCCESS(f"Queued {count} task(s)."))
