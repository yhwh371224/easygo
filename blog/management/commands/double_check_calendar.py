from datetime import date, timedelta
from django.core.management.base import BaseCommand
from utils.email import send_text_email
from blog.models import Post
from main.settings import RECIPIENT_EMAIL


class Command(BaseCommand):
    help = 'Double check calendar'

    def handle(self, *args, **options):
        start_date = date.today() + timedelta(days=1)
        end_date = date.today() + timedelta(days=3)

        upcoming_bookings = Post.objects.filter(
            pickup_date__range=(start_date, end_date)
        ).only("name", "email", "pickup_date", "calendar_event_id")

        for booking in upcoming_bookings:
            self.check_and_notify_missing_calendar_id(booking)
            
    def check_and_notify_missing_calendar_id(self, booking):
        if not booking.calendar_event_id:
            subject = f"Empty calendar ID for {booking.pickup_date}"
            message = f"{booking.name} & {booking.email}"
            recipient_list = [RECIPIENT_EMAIL]
            send_text_email(subject, message, recipient_list)

