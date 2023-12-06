import os
import logging
import threading
from django.core.management.base import BaseCommand
from blog.models import Post
from datetime import datetime, timedelta
from retrieve import main 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger('blog.update_reminder')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(message)s')

# Create the logs directory if it doesn't exist
logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'update_reminder.log'))
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


class Command(BaseCommand):
    help = 'Update reminders for posts'

    def __init__(self):
        self.lock = threading.Lock()

    def handle(self, *args, **options):
        my_list = main()  # Call the main function to get the list
        unique_emails = set()  # Use a set to store unique email addresses

        today = datetime.now()
        three_days_later = today + timedelta(days=3)
        
        with self.lock:
            for list_email in my_list:
                # Check if the email address has already been processed
                if list_email in unique_emails:
                    continue
                else: 
                    unique_emails.add(list_email)

                    posts = Post.objects.filter(email__iexact=list_email, flight_date__range=[today, three_days_later])

                    for post in posts:
                        if post.reminder:
                            continue
                        else: 
                            post.reminder = True
                            post.save()

                            logger.info(f'....Just now executed:{post.name}, {post.flight_date}, {post.pickup_time}')
