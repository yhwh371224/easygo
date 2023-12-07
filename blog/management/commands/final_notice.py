import os
import logging 
import threading
from django.core.management.base import BaseCommand
from datetime import date, timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from main.settings import RECIPIENT_EMAIL


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger('blog.final_notice')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(message)s')

# Create the logs directory if it doesn't exist
logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'final_notice.log'))
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


class Command(BaseCommand):
    help = 'Send final notices'

    def __init__(self):
        self.lock = threading.Lock()

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        final_notices = Post.objects.filter(flight_date=tomorrow)
        
        for final_notice in final_notices:

            if not final_notice.reminder:

                if final_notice.cancelled or final_notice.paid:
                    logger.info(f'........{final_notice.name}, {final_notice.pickup_time}, paid:{final_notice.paid} | cancelled:{final_notice.cancelled}')
                    continue
            
                else:                    
                    with self.lock:
                        html_content = render_to_string("basecamp/html_email-fnotice.html",
                                                        {'name': final_notice.name, 'email': final_notice.email})
                        text_content = strip_tags(html_content)
                        email = EmailMultiAlternatives("Final notice", text_content, '', [final_notice.email, RECIPIENT_EMAIL])
                        email.attach_alternative(html_content, "text/html")
                        email.send()

                        logger.info(f'........final notice email sent: {final_notice.name}, {final_notice.pickup_time}')

                
        
        
