import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from main.settings import RECIPIENT_EMAIL


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'Not payment received yet'

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_bookings = Post.objects.filter(flight_date=tomorrow)
        
        for tomorrow_booking in tomorrow_bookings:

            if not tomorrow_booking.cancelled and not tomorrow_booking.paid and not tomorrow_booking.cash:
                html_content = render_to_string("basecamp/html_email-nopayment.html",
                                                {'name': tomorrow_booking.name, 'email': tomorrow_booking.email})
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives("Payment notice", text_content, '', [tomorrow_booking.email, RECIPIENT_EMAIL])
                email.attach_alternative(html_content, "text/html")
                email.send()

        today = date.today()
        today_bookings = Post.objects.filter(flight_date=today)

        for today_booking in today_bookings: 

            if not today_booking.cancelled and not today_booking.paid and not today_booking.cash: 
                html_content = render_to_string("basecamp/html_email-nopayment-today.html",
                                                {'name': today_booking.name, 'email': today_booking.email})
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives("Urgent payment notice", text_content, '', [today_booking.email, RECIPIENT_EMAIL])
                email.attach_alternative(html_content, "text/html")
                email.send()

            