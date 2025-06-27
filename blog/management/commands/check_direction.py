from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from blog.models import Post
from main.settings import RECIPIENT_EMAIL


class Command(BaseCommand):
    help = 'Check bookings with flight number but missing direction'

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
            end_date = today + timedelta(days=14)

            bookings = Post.objects.filter(
                pickup_date__range=(start_date, end_date)
            ).exclude(cancelled=True)

            missing_direction_list = []

            for booking in bookings:
                flight_number = booking.flight_number.strip() if booking.flight_number else ''
                direction = booking.direction.strip() if booking.direction else ''

                if flight_number and not direction:
                    missing_direction_list.append({
                        'name': booking.name,
                        'email': booking.email,
                        'pickup_date': booking.pickup_date,
                        'flight_number': booking.flight_number,
                    })

            if missing_direction_list:
                email_subject = "Summary: Bookings with Flight Number but Missing Direction"
                email_template = "basecamp/html_email-missing-direction.html"

                self.send_email(
                    email_subject,
                    email_template,
                    {'bookings': missing_direction_list},
                    [RECIPIENT_EMAIL]
                )
                self.stdout.write(self.style.SUCCESS(f'Missing direction summary sent. Total: {len(missing_direction_list)}'))
            else:
                self.stdout.write(self.style.SUCCESS('No bookings with missing direction found.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send missing direction summary: {str(e)}'))