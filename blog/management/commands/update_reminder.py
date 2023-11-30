import logging
from django.core.management.base import BaseCommand
from blog.models import Post
from datetime import datetime, timedelta
from retrieve import main 


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update reminders for posts'

    def handle(self, *args, **options):
        updated = 0  # Initialize the counter
        my_list = main()  # Call the main function to get the list

        today = datetime.now()
        three_days_later = today + timedelta(days=3)

        try:
            for list_email in my_list:      

                posts = Post.objects.filter(email__iexact=list_email, flight_date__range=[today, three_days_later])

                for post in posts:
                    post.reminder = True
                    post.save()
                    updated += 1

                    logger.info(f'Updated reminder for {post.name}, {post.flight_date}, {post.pickup_time}')
                    self.stdout.write(self.style.SUCCESS(f'Updated reminder for {post.name}, {post.flight_date}, {post.pickup_time}'))

            logger.info(f'Successfully updated reminders for {updated} posts')
            self.stdout.write(self.style.SUCCESS(f'Successfully {updated} updated reminders'))

        except Exception as e:
            logger.exception(f"Error during reminder update: {e}")

