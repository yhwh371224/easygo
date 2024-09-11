from django.core.management.base import BaseCommand
from blog.models import Post, Inquiry


class Command(BaseCommand):
    help = 'Delete all Inquiry objects where the email exists in Post'

    def handle(self, *args, **kwargs):
        post_emails = Post.objects.values_list('email', flat=True)

        inquiries_to_delete = Inquiry.objects.filter(email__in=post_emails)
        deleted_count, _ = inquiries_to_delete.delete()

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} Inquiry objects'))
