import threading
import logging
import os 
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from django.utils import timezone
from main.settings import RECIPIENT_EMAIL


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

    def send_email_task(self, posts, template_name, subject):
        with self.lock:
            for post in posts:
                if not post.sent_email:
                    post.sent_email = True
                    post.save(update_fields=['sent_email'])

                    html_content = render_to_string(template_name, {
                        'company_name': post.company_name,
                        'name': post.name,
                        'contact': post.contact,
                        'email': post.email,
                        'email1': post.email1,
                        'pickup_date': post.pickup_date,
                        'flight_number': post.flight_number,
                        'flight_time': post.flight_time,
                        'pickup_time': post.pickup_time,
                        'return_direction': post.return_direction,
                        'return_pickup_date': post.return_pickup_date,
                        'return_flight_number': post.return_flight_number,
                        'return_flight_time': post.return_flight_time,
                        'return_pickup_time': post.return_pickup_time,
                        'direction': post.direction,
                        'street': post.street,
                        'suburb': post.suburb,
                        'no_of_passenger': post.no_of_passenger,
                        'no_of_baggage': post.no_of_baggage,
                        'message': post.message,
                        'notice': post.notice,
                        'price': post.price,
                        'paid': post.paid
                    })
                    text_content = strip_tags(html_content)
                    email = EmailMultiAlternatives(subject, text_content, '', [post.email, post.email1, RECIPIENT_EMAIL])
                    email.attach_alternative(html_content, "text/html")
                    email.send()





          