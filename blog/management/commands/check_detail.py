from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from basecamp.utils import render_email_template


class Command(BaseCommand):
    help = 'Check bookings with missing details (consolidated report)'

    def send_email(self, subject, template, context, recipient_list):
        html_content = render_email_template(template, context)
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(subject, text_content, '', recipient_list)
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

    def handle(self, *args, **options):
        try:
            today = date.today()
            start_date = today + timedelta(days=1)
            end_date = today + timedelta(days=30)

            bookings = Post.objects.filter(
                pickup_date__range=(start_date, end_date)
            ).exclude(cancelled=True)

            fields_to_check = ['pickup_time']  # 원하는 일반 필드 추가

            consolidated_list = []

            for booking in bookings:
                issues = []

                # flight_number = (booking.flight_number or '').strip()
                # direction = (booking.direction or '').strip()

                # if flight_number and not direction:
                #     issues.append('Direction missing (flight number present)')


                for field in fields_to_check:
                    value = getattr(booking, field, None)
                    value = value.strip() if value else ''

                    if not value:
                        issues.append(f'{field.replace("_", " ").capitalize()} missing')

                if issues:
                    print(f'Adding to consolidated_list: {booking.name}, Issues: {issues}')
                    consolidated_list.append({
                        'name': booking.name,
                        'email': booking.email or 'N/A',
                        'pickup_date': booking.pickup_date,
                        'issues': '; '.join(issues)
                    })

            if consolidated_list:
                email_subject = "Summary: Bookings with Missing Details"
                email_template = "html_email-missing-details.html"

                self.send_email(
                    email_subject,
                    email_template,
                    {'bookings': consolidated_list},
                    [RECIPIENT_EMAIL]
                )

                self.stdout.write(self.style.SUCCESS(
                    f'Missing details summary sent. Total problematic bookings: {len(consolidated_list)}'
                ))
            else:
                self.stdout.write(self.style.SUCCESS('No bookings with missing details found.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send summary: {str(e)}'))
