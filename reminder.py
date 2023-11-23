import logging
import os
import django

from blog.models import Post
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from simplegmail import Gmail

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
django.setup()


def update_posts_with_reminders():
    try:
        today = datetime.now()
        three_days_later = today + timedelta(days=3)

        gmail = Gmail()

        messages = gmail.get_reminder_messages()

        for message in messages:
            filtered_posts = Post.objects.filter(email=message.recipient, flight_date__range=[today, three_days_later])

            if filtered_posts.exists():
                posts_to_update = list(filtered_posts)
                
                for post in posts_to_update:
                    post.reminder = True
                    post.save()

    except Exception as e:
        logging.error(f"An error occurred while updating posts with reminders: {e}")

if __name__ == "__main__":
    update_posts_with_reminders()


    

