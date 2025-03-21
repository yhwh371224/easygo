import logging
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from utils.email_helper import EmailSender

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send reminders for payment'

    def handle(self, *args, **options):
        try:
            start_date = date.today()
            end_date = start_date + timedelta(days=3)

            bookings = Post.objects.filter(pickup_date__range=(start_date, end_date))

            for booking in bookings:
                email_cases = [
                    (("Urgent notice for payment", "basecamp/html_email-nopayment-today.html")
                        if (booking.pickup_date - start_date).days in [0, 1]
                        else ("Payment notice", "basecamp/html_email-nopayment.html"),
                        {'name': booking.name, 'email': booking.email, 'price': booking.price}),

                    (("Urgent notice for payment discrepancy", "basecamp/html_email-response-discrepancy.html"),
                        {'name': booking.name, 'price': booking.price, 'paid': booking.paid,
                        'diff': round(float(booking.price) - float(booking.paid), 2)})
                ]

                for (subject, template), context in email_cases:
                    EmailSender.send(subject, template, context, [booking.email, RECIPIENT_EMAIL])

            self.stdout.write(self.style.SUCCESS('No_payment_yet emailed successfully'))

        except Exception as e:
            logger.error(f"Failed to send no_payment_yet: {str(e)}", exc_info=True)
            self.stdout.write(self.style.ERROR(f'Failed to send no_payment_yet: {str(e)}'))

        
