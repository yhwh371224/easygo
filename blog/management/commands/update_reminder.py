import os
import threading
from django.core.management.base import BaseCommand
from blog.models import Post
from datetime import datetime, timedelta
from retrieve import main 


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'Update reminders for posts'

    def __init__(self):
        self.lock = threading.Lock()

    def handle(self, *args, **options):
        my_list = main()  
        unique_emails = set() 

        today = datetime.now()
        three_days_later = today + timedelta(days=3)
        
        with self.lock:
            for list_email in my_list:
                if list_email in unique_emails:
                    continue
                else: 
                    unique_emails.add(list_email)

                    posts = Post.objects.filter(email__iexact=list_email, pickup_date__range=[today, three_days_later])

                    for post in posts:
                        if not post.reminder:
                            post.reminder = True
                            post.save(update_fields=['reminder'])

