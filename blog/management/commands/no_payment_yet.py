from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from main.settings import RECIPIENT_EMAIL


class Command(BaseCommand):
    help = 'Send reminders for payment'

    def send_email(self, subject, template, context, recipient_list):
        html_content = render_to_string(template, context)
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
        try:
            start_date = date.today()
            end_date = start_date + timedelta(days=7)

            bookings = Post.objects.filter(
                pickup_date__range=(start_date, end_date),
                cash=False,
                cancelled=False
            )

            for booking in bookings:
                # ----------------------------
                # 1. 결제 미완료 메일
                # ----------------------------
                if booking.paid is None or booking.paid.strip() in ["", "0"]:
                    days_difference = (booking.pickup_date - start_date).days
                    if days_difference in [0, 1, 2]:
                        email_subject = "Urgent notice for payment"
                        template = "basecamp/html_email-nopayment-today.html" \
                            if not booking.cash \
                            else "basecamp/html_email-nopayment-today-1.html"
                    else:
                        email_subject = "Payment notice"
                        template = "basecamp/html_email-nopayment.html" \
                            if not booking.cash \
                            else "basecamp/html_email-nopayment-1.html"

                    display_date = self.get_display_date(booking)
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
                        },
                        [booking.email, RECIPIENT_EMAIL]
                    )

                # ----------------------------
                # 2. 결제 차액 메일
                # ----------------------------
                if booking.paid is not None:
                    price = float(booking.price or 0)
                    paid = float(booking.paid or 0)
                    if price > paid:
                        diff = round(price - paid, 2)
                        display_date = self.get_display_date(booking)
                        self.send_email(
                            "Urgent notice for payment discrepancy",
                            "basecamp/html_email-response-discrepancy.html",
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

            self.stdout.write(self.style.SUCCESS('No_payment_yet emailed successfully'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send no_payment_yet: {str(e)}'))
