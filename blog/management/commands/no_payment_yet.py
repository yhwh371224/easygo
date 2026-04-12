import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email, collect_recipients


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send reminders for payment'

    def get_display_date(self, booking):
        if booking.return_pickup_time == 'x':
            if booking.return_pickup_date and booking.return_pickup_date < date.today():
                return str(booking.pickup_date)
            else:
                return f"{booking.pickup_date} & {booking.return_pickup_date}"
        return str(booking.pickup_date)

    def handle(self, *args, **options):       
        today = date.today() 
        start_date = date.today() + timedelta(days=1)
        end_date = start_date + timedelta(days=21)

        bookings = Post.objects.filter(
            pickup_date__range=(start_date, end_date),
            cash=False,
            cancelled=False,
        )

        for booking in bookings:
            display_date = self.get_display_date(booking)  # 먼저 계산

            try: 
                # paid 값 float로 안전하게 변환
                price = float(booking.price or 0)
                paid = float(booking.paid or 0)

                # ----------------------------
                # 1. 결제 미완료 메일
                # ----------------------------
                if booking.paid is None or booking.paid == "" or paid == 0:
                    days_difference = (booking.pickup_date - start_date).days
                    if days_difference <= 2:
                        email_subject = "Urgent notice for payment"
                        template = "html_email-nopayment-today.html" 
                            
                    else:
                        email_subject = "Payment notice"
                        template = "html_email-nopayment.html"                             

                    send_template_email(
                        email_subject,
                        template,
                        {
                            'booker_name': booking.booker_name,
                            'name': booking.name,
                            'email': booking.email,
                            'price': booking.price,
                            'pickup_date': booking.pickup_date,
                            'return_pickup_date': booking.return_pickup_date,
                            'display_date': display_date,
                            "prepay": booking.prepay,
                        },
                        collect_recipients(booking.email, None, RECIPIENT_EMAIL)
                    )

                # ----------------------------
                # 2. 결제 차액 메일
                # ----------------------------
                elif 0 < paid < price:
                    diff = round(price - paid, 2)
                    send_template_email(
                        "Urgent notice for payment discrepancy",
                        "html_email-response-discrepancy.html",
                        {
                            'booker_name': booking.booker_name,
                            'name': booking.name,
                            'price': booking.price,
                            'paid': booking.paid,
                            'diff': diff,
                            'pickup_date': booking.pickup_date,
                            'return_pickup_date': booking.return_pickup_date,
                            'display_date': display_date,
                        },
                        collect_recipients(booking.email, None, RECIPIENT_EMAIL)
                    )
            
            except Exception as e:
                logger.error(f"Failed to send email for booking {booking.id} ({booking.email}): {e}")
                self.stdout.write(self.style.ERROR(f"Failed to send email for {booking.email}: {e}"))

        self.stdout.write(self.style.SUCCESS('No_payment_yet emailed successfully'))


