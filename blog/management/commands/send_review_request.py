import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
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
            email = booking_reminder.email
            uid = urlsafe_base64_encode(force_bytes(email))
            review_link = f"{settings.SITE_URL}/verify-email/{uid}/"

            html_content = render_to_string("basecamp/html_email-yesterday.html", {
                'name': booking_reminder.name,
                'review_link': review_link,
            })

            text_content = strip_tags(html_content)
            email_message = EmailMultiAlternatives("Review-EasyGo", text_content, settings.DEFAULT_FROM_EMAIL, [email])
            email_message.attach_alternative(html_content, "text/html")

            try:
                email_message.send(fail_silently=False)
                print(f"Email sent to {email} for {booking_reminder.name}")
            except Exception as e:
                print(f"Failed to send review request email to {email} | {booking_reminder.pickup_date}: {e}")
