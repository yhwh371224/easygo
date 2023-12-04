import threading
import logging
import os 
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from datetime import date, timedelta
from django.utils import timezone
from main.settings import RECIPIENT_EMAIL

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger('blog.confirm_booking')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(message)s')

# Create the logs directory if it doesn't exist
logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'confirm_booking.log'))
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

class Command(BaseCommand):
    help = 'Send booking confirmation'

    def __init__(self):
        self.lock = threading.Lock()

    def handle(self, *args, **options):
        self.send_email()

    def send_email(self):
        current_datetime = timezone.localtime(timezone.now())
        posts = Post.objects.filter(created__date=current_datetime.date())
        
        if posts.exists():
            self.send_email_task(posts, "basecamp/html_email-confirmation.html", "EasyGo Booking confirmation")
        else:
            logger.info("No upcoming flights today.")

    def send_email_task(self, posts, template_name, subject):
        # sent_emails_set = set()  
        
        for post in posts:

            if post.sent_email:
                logger.info(f'....Already sent: {post.name}, {post.flight_date}, {post.pickup_time}')
                continue 

            else:
                with self.lock:

                    html_content = render_to_string(template_name, {
                        'company_name': post.company_name, 'name': post.name, 'contact': post.contact, 'email': post.email, 'email1': post.email1, 
                        'flight_date': post.flight_date, 'flight_number': post.flight_number, 'flight_time': post.flight_time, 'pickup_time': post.pickup_time, 
                        'return_direction': post.return_direction,'return_flight_date': post.return_flight_date, 'return_flight_number': post.return_flight_number, 
                        'return_flight_time': post.return_flight_time, 'return_pickup_time': post.return_pickup_time, 'direction': post.direction, 'street': post.street, 
                        'suburb': post.suburb, 'no_of_passenger': post.no_of_passenger, 'no_of_baggage': post.no_of_baggage, 'message': post.message, 'notice': post.notice , 
                        'price': post.price, 'paid': post.paid }
                    )
                    text_content = strip_tags(html_content)
                    email = EmailMultiAlternatives(subject, text_content, '', [post.email, RECIPIENT_EMAIL])
                    email.attach_alternative(html_content, "text/html")
                    email.send() 

                    post.sent_email = True
                    post.save()

                    logger.info(f'........{subject}: {post.name}, {post.flight_date}, {post.pickup_time}')

                    # if post.email not in sent_emails_set:
                    #     sent_emails_set.add(post.email)              