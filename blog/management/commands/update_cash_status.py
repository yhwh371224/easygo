from django.core.management.base import BaseCommand
from blog.models import Post
from utils.gmail_utils import fetch_cash_emails as get_cash_emails_list


class Command(BaseCommand):
    help = 'Update the cash status for posts based on "cash" labeled emails (using retrieve_cash.py).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Fetching cash-related emails from Gmail API via retrieve_cash.py..."))

        my_list = get_cash_emails_list()

        if not my_list:
            self.stdout.write(self.style.WARNING("No cash-related emails found. Exiting."))
            return

        unique_emails = set(email.lower() for email in my_list)
        updated_count = 0

        self.stdout.write(self.style.NOTICE(f"Found {len(unique_emails)} unique emails to process."))

        posts_to_update = Post.objects.filter(
            email__in=unique_emails,
            cash=False,
        )

        for post in posts_to_update:
            try:
                post.cash = True
                post.reminder = True
                post.pending = False
                post.cancelled = False
                post.save(update_fields=['cash', 'reminder', 'pending', 'cancelled'])
                updated_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated post (ID: {post.pk}) to cash=True for email: {post.email}"
                    )
                )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving post ID {post.pk}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n--- Total Update Complete ---"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Total {updated_count} Post records were individually updated to cash=True."
            )
        )
