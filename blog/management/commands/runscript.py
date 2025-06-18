from django.core.management.base import BaseCommand
from blog.models import Post


class Command(BaseCommand):
    help = "Update kate@diveplanit.com to heather@blueplanetdc.com and move old email to email1"

    def handle(self, *args, **options):
        target_email = "kate@diveplanit.com"
        new_email = "heather@blueplanetdc.com"
        new_contact = "+12404819639"

        posts = Post.objects.filter(email__iexact=target_email)

        count = 0
        for post in posts:
            if not post.email1:
                post.email1 = target_email
            post.email = new_email
            post.contact = new_contact
            post.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f"{count} posts updated."))
