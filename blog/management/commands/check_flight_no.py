import re

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from main.settings import RECIPIENT_EMAIL, DEFAULT_FROM_EMAIL


class Command(BaseCommand):
    help = 'Check for missing flight or contact numbers and send reminder emails'

    def send_email(self, subject, template, context, recipient_list):
        html_content = render_to_string(template, context)
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(subject, text_content, '', recipient_list)
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

    def handle(self, *args, **options):
        try:
            today = date.today()
            start_date = today + timedelta(days=1)
            end_date = today + timedelta(days=5)

            bookings = Post.objects.filter(pickup_date__range=(start_date, end_date))

            for booking in bookings:
                contact_issue = False
                flight_issue = False
                issues = []

                contact = booking.contact.strip() if booking.contact else ''
                cleaned_contact = ''.join(filter(str.isdigit, contact))
                contact_issue = not cleaned_contact or len(cleaned_contact) < 10 or len(cleaned_contact) > 16

                if contact_issue:
                    issues.append('Contact number is missing or invalid')

                if booking.direction and booking.direction.strip().lower() in ['pickup from intl airport', 'pickup from domestic airport']:
                    flight_number = booking.flight_number.strip() if booking.flight_number else ''                    
                    flight_number_cleaned = re.sub(r'[^A-Za-z0-9]', '', flight_number).upper()
                    
                    match = re.match(r'^([A-Z]{2,3})(\d+)$', flight_number_cleaned)

                    flight_valid = False
                    if match:
                        airline_code = match.group(1)
                        number_part_raw = match.group(2)
                       
                        if len(number_part_raw) > 4:
                            flight_valid = False
                        else:
                            number_part = str(int(number_part_raw))  
                            flight_number_final = airline_code + number_part
                            flight_valid = bool(re.match(r'^[A-Z]{2,3}\d{1,4}$', flight_number_final))

                    flight_issue = not flight_valid
                    if flight_issue:
                        issues.append('Flight number is missing or invalid')

                if contact_issue or flight_issue:
                    email_subject = "Missing or Invalid Flight/Contact Information Reminder"
                    email_template = "basecamp/html_email-missing-flight-contact.html"

                    self.send_email(
                        email_subject,
                        email_template,
                        {
                            'name': booking.name,
                            'email': booking.email,
                            'pickup_date': booking.pickup_date,
                            'direction': booking.direction,
                            'flight_number': booking.flight_number,
                            'contact': booking.contact,
                            'issues': issues,
                        },
                        [booking.email, RECIPIENT_EMAIL]
                    )

            self.stdout.write(self.style.SUCCESS('Missing flight/contact number reminders sent successfully'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send missing flight/contact number reminders: {str(e)}'))
