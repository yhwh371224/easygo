import os
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from blog.models import Post

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'Send review requests for yesterday\'s bookings'

    def handle(self, *args, **options):
        self.send_review_requests()

    def send_review_requests(self):
        target_date = date.today() - timedelta(days=1)
        booking_reminders = Post.objects.filter(pickup_date=target_date, cancelled=False)

        for booking_reminder in booking_reminders:
            user = booking_reminder.user
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            review_link = f"{self.request.build_absolute_uri(f'/verify-email/{uid}/{token}/')}"

            html_content = render_to_string("basecamp/html_email-yesterday.html", {
                'name': booking_reminder.name,
                'review_link': review_link,
            })

            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives("Review-EasyGo", text_content, settings.DEFAULT_FROM_EMAIL, [booking_reminder.email])
            email.attach_alternative(html_content, "text/html")

            try:
                email.send(fail_silently=False)
            except Exception as e:
                print(f"Failed to send review request email to {booking_reminder.email} | {booking_reminder.pickup_date}: {e}")
