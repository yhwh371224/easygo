import logging
from django.core.management.base import BaseCommand
from blog.models import Post
from django.utils import timezone
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send booking confirmation'

    def handle(self, *args, **options):
        self.send_email()

    def send_email(self):
        current_datetime = timezone.localtime(timezone.now())
        posts = Post.objects.filter(created__date=current_datetime.date())

        if posts.exists():
            self.send_email_task(posts, "html_email-confirmation.html", "EasyGo Booking confirmation")

    def send_email_task(self, posts, template_name, subject):
        to_update = []
        email_tasks = []

        for post in posts:
            if not post.sent_email:
                post.sent_email = True
                to_update.append(post)

                context = {
                    'company_name': post.company_name,
                    'booker_name': post.booker_name,
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
                    'paid': post.paid,
                }
                email_tasks.append((subject, template_name, context, [post.email, post.email1, RECIPIENT_EMAIL]))

        if to_update:
            Post.objects.bulk_update(to_update, ['sent_email'], batch_size=50)
            for args in email_tasks:
                send_template_email(*args)
