from django.core.management.base import BaseCommand
from blog.models import Post


class Command(BaseCommand):    

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


# updated = Post.objects.filter(email="heather@blueplanetdc.com").update(email="sungkam718@gmail.com")
# updated = Post.objects.filter(email="sungkam718@gmail.com").update(email="heather@blueplanetdc.com")


# class Command(BaseCommand):

#     def handle(self, *args, **kwargs):
#         old_email = "heather@blueplanetdc.com"
#         new_email = "sungkam718@gmail.com"
#         updated = Post.objects.filter(email__iexact=old_email).update(email=new_email)


# class Command(BaseCommand):

#     def handle(self, *args, **kwargs):
#         target_email = "kate@diveplanit.com"
#         cleared = Post.objects.filter(email__iexact=target_email).update(email1="")
        