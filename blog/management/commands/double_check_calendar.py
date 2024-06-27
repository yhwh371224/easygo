import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from blog.models import Post, Driver
from main.settings import RECIPIENT_EMAIL


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Command(BaseCommand):
    help = 'Double check calendar'

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_bookings = Post.objects.filter(pickup_date=tomorrow)
        
        for booking in tomorrow_bookings:
            self.check_and_notify_missing_calendar_id(booking)
            self.confirm_booking(booking)
            self.assign_default_driver(booking)
            
    def check_and_notify_missing_calendar_id(self, booking):
        if not booking.calendar_event_id:
            subject = "Empty calendar ID for tomorrow"
            message = f"{booking.name} & {booking.email}"
            recipient_list = [RECIPIENT_EMAIL]
            send_mail(subject, message, '', recipient_list, fail_silently=False)

    def confirm_booking(self, booking):
        if not booking.cancelled:
            booking.is_confirmed = True
            booking.save(update_fields=['is_confirmed'])

    def assign_default_driver(self, booking):
        if booking.driver is None:
            sam_driver = Driver.objects.get(driver_name="Sam")
            booking.driver = sam_driver
            booking.save(update_fields=['driver'])

            