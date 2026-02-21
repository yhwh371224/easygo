import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.db.models import Q
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from basecamp.utils import render_email_template


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send reminders for payment'

    def send_email(self, subject, template, context, recipient_list):
        html_content = render_email_template(template, context)
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(subject, text_content, '', recipient_list)
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

    def get_display_date(self, booking):
        if booking.return_pickup_time == 'x':
            if booking.return_pickup_date and booking.return_pickup_date < date.today():
                return str(booking.pickup_date)
            else:
                return f"{booking.pickup_date} & {booking.return_pickup_date}"
        return str(booking.pickup_date)

    def handle(self, *args, **options):        
        start_date = date.today() + timedelta(days=1)
        end_date = start_date + timedelta(days=14)

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

                    self.send_email(
                        email_subject,
                        template,
                        {
                            'name': booking.name,
                            'email': booking.email,
                            'price': booking.price,
                            'pickup_date': booking.pickup_date,
                            'return_pickup_date': booking.return_pickup_date,
                            'display_date': display_date,
                            "prepay": booking.prepay,
                        },
                        [booking.email, RECIPIENT_EMAIL]
                    )

                # ----------------------------
                # 2. 결제 차액 메일
                # ----------------------------
                elif 0 < paid < price:
                    diff = round(price - paid, 2)
                    self.send_email(
                        "Urgent notice for payment discrepancy",
                        "html_email-response-discrepancy.html",
                        {
                            'name': booking.name,
                            'price': booking.price,
                            'paid': booking.paid,
                            'diff': diff,
                            'pickup_date': booking.pickup_date,
                            'return_pickup_date': booking.return_pickup_date,
                            'display_date': display_date,
                        },
                        [booking.email, RECIPIENT_EMAIL]
                    )
            
            except Exception as e:
                logger.error(f"Failed to send email for booking {booking.id} ({booking.email}): {e}")
                self.stdout.write(self.style.ERROR(f"Failed to send email for {booking.email}: {e}"))

        self.stdout.write(self.style.SUCCESS('No_payment_yet emailed successfully'))


