import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from main.settings import RECIPIENT_EMAIL


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'Double check calendar'

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_bookings = Post.objects.filter(flight_date=tomorrow)
        
        for tomorrow_booking in tomorrow_bookings:

            if not tomorrow_booking.calendar_event_id:
                subject = "empty calendar id from double_check_calendar.py"
                message = f"{tomorrow_booking.name} & {tomorrow_booking.email}"
                recipient_list = [RECIPIENT_EMAIL]

                send_mail(subject, message, '', recipient_list)

            if not tomorrow_booking.cancelled:
                tomorrow_booking.is_confirmed = True
                tomorrow_booking.save()

            