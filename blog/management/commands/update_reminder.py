from django.core.management.base import BaseCommand
from blog.models import Post
from datetime import datetime, timedelta
from retrieve import main


class Command(BaseCommand):
    help = 'Update reminders for posts'

    def handle(self, *args, **options):
        # 이메일 모두 소문자로 변환
        my_list = [email.lower() for email in main()]
        unique_emails = set()

        today = datetime.now()
        three_days_later = today + timedelta(days=3)

        for list_email in my_list:
            if list_email in unique_emails:
                continue
            else:
                unique_emails.add(list_email)

                # DB에서도 소문자로 변환해서 비교
                posts = Post.objects.filter(
                    pickup_date__range=[today, three_days_later]
                )

                for post in posts:
                    if post.email.lower() == list_email and not post.reminder:
                        post.reminder = True
                        post.cancelled = False
                        post.pending = False
                        post.save(update_fields=['reminder', 'cancelled', 'pending'])
