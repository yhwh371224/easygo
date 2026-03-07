import re

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email


class Command(BaseCommand):
    help = 'Check for missing flight or contact numbers and send reminder emails'

    def handle(self, *args, **options):
        try:
            today = date.today()
            start_date = today
            end_date = today + timedelta(days=21)

            bookings = Post.objects.filter(
                pickup_date__range=(start_date, end_date)
            ).exclude(cancelled=True)

            for booking in bookings:
                contact_issue = False
                flight_issue = False
                issues = []

                contact = booking.contact.strip() if booking.contact else ''
                cleaned_contact = ''.join(filter(str.isdigit, contact))
                contact_issue = not cleaned_contact or len(cleaned_contact) < 9 or len(cleaned_contact) > 13

                if contact_issue:
                    issues.append('Contact number is missing or invalid')

                if booking.direction and booking.direction.strip().lower() in ['pickup from intl airport', 'pickup from domestic airport']:
                    flight_number = booking.flight_number.strip() if booking.flight_number else ''                    
                    flight_number_cleaned = re.sub(r'[^A-Za-z0-9]', '', flight_number).upper()
                    
                    flight_valid = False

                    # Special exception for exactly '5j39' (case-insensitive)
                    if flight_number_cleaned.lower() == '5j39':
                        flight_valid = True
                    else:
                        match = re.match(r'^([A-Z]{1,3})(\d+)$', flight_number_cleaned)

                        if match:
                            airline_code = match.group(1)
                            number_part_raw = match.group(2)
                            number_part_no_zero = number_part_raw.lstrip('0')

                            if len(number_part_no_zero) <= 4:
                                number_part = str(int(number_part_raw))  
                                flight_number_final = airline_code + number_part
                                flight_valid = bool(re.match(r'^[A-Z]{1,3}\d{1,4}$', flight_number_final))

                    flight_issue = not flight_valid
                    if flight_issue:
                        issues.append('Flight number is missing or invalid')

                if contact_issue or flight_issue:
                    send_template_email(
                        "Missing or Invalid Flight/Contact Information Reminder",
                        "html_email-missing-flight-contact.html",
                        {
                            'name': booking.name,
                            'email': booking.email,
                            'pickup_date': booking.pickup_date,
                            'direction': booking.direction,
                            'flight_number': booking.flight_number,
                            'contact': booking.contact,
                            'issues': issues,
                        },
                        [booking.email, RECIPIENT_EMAIL],
                        fail_silently=False,
                    )

            self.stdout.write(self.style.SUCCESS('Missing flight/contact number reminders sent successfully'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send missing flight/contact number reminders: {str(e)}'))
