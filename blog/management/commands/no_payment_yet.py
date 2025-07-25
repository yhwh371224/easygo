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
        
    def handle(self, *args, **options):
        try: 
            start_date = date.today()
            end_date = start_date + timedelta(days=7)

            bookings = Post.objects.filter(pickup_date__range=(start_date, end_date))
                
            for booking in bookings:
                if not booking.cash and (booking.paid is None or booking.paid.strip() in ["", "0"]) and not booking.cancelled:
                    days_difference = (booking.pickup_date - start_date).days
                    if days_difference in [0, 1, 2]:  
                        email_subject = "Urgent notice for payment"

                        if booking.prepay or booking.company_name:                        
                            email_template = "basecamp/html_email-nopayment-today.html"
                        else: 
                            email_template = "basecamp/html_email-nopayment-today-1.html"
                        
                    else:
                        email_subject = "Payment notice"

                        if booking.prepay or booking.company_name:                        
                            email_template = "basecamp/html_email-nopayment.html"
                        else: 
                            email_template = "basecamp/html_email-nopayment-1.html"

                    # 날짜 표시 조건 처리
                    if booking.return_pickup_time == 'x':
                        if booking.return_pickup_date and booking.return_pickup_date < date.today():
                            display_date = f"{booking.pickup_date}"
                        else:
                            display_date = f"{booking.pickup_date} & {booking.return_pickup_date}"
                    else:
                        display_date = f"{booking.pickup_date}"

                    self.send_email(
                        email_subject,
                        email_template,
                        {'name': booking.name, 'email': booking.email, 'price': booking.price, 
                         'pickup_date': booking.pickup_date, 
                         'return_pickup_date': booking.return_pickup_date,
                         'display_date': display_date},
                        [booking.email, RECIPIENT_EMAIL]
                    )

                if booking.paid is not None and float(booking.price or 0) > float(booking.paid or 0):
                    diff = round(float(booking.price or 0) - float(booking.paid or 0), 2)

                    # 날짜 표시 조건 처리
                    if booking.return_pickup_time == 'x':
                        if booking.return_pickup_date and booking.return_pickup_date < date.today():
                            display_date = f"{booking.pickup_date}"
                        else:
                            display_date = f"{booking.pickup_date} & {booking.return_pickup_date}"
                    else:
                        display_date = f"{booking.pickup_date}"

                    email_subject = "Urgent notice for payment discrepancy"
                    email_template = "basecamp/html_email-response-discrepancy.html"
                    self.send_email(
                        email_subject,
                        email_template,
                        {'name': booking.name, 'price': booking.price, 'paid': booking.paid, 
                         'diff': diff, 'pickup_date': booking.pickup_date, 
                         'display_date': display_date, 'return_pickup_date': booking.return_pickup_date},                    
                        [booking.email, RECIPIENT_EMAIL]
                    )

            self.stdout.write(self.style.SUCCESS('No_payment_yet emailed successfully'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send no_payment_yet: {str(e)}'))
        
