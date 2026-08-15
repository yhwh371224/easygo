import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from utils.command_alerts import TelegramAlertMixin
from utils.email import send_template_email


logger = logging.getLogger(__name__)


class Command(TelegramAlertMixin, BaseCommand):
    alert_header = 'check_detail 실패'

    help = 'Check bookings with missing details (consolidated report)'

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

                send_template_email(
                    email_subject,
                    email_template,
                    {'bookings': consolidated_list},
                    [RECIPIENT_EMAIL],
                    fail_silently=False,
                )

                self.stdout.write(self.style.SUCCESS(
                    f'Missing details summary sent. Total problematic bookings: {len(consolidated_list)}'
                ))
            else:
                self.stdout.write(self.style.SUCCESS('No bookings with missing details found.'))

        except Exception as e:
            logger.exception('check_detail: failed to send summary')
            self.stdout.write(self.style.ERROR(f'Failed to send summary: {str(e)}'))
            self.alerts.append(f"❌ 누락정보 요약 리포트 발송 실패 | {str(e)[:150]}")
