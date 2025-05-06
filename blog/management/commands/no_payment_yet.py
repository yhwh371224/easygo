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
            end_date = start_date + timedelta(days=3)

            bookings = Post.objects.filter(pickup_date__range=(start_date, end_date))
                
            for booking in bookings:
                if not booking.cash and not booking.paid and not booking.cancelled:
                    days_difference = (booking.pickup_date - start_date).days
                    if days_difference in [0, 1]:  
                        email_subject = "Urgent notice for payment"
                        email_template = "basecamp/html_email-nopayment-today.html"
                    else:
                        email_subject = "Payment notice"
                        email_template = "basecamp/html_email-nopayment.html"

                    self.send_email(
                        email_subject,
                        email_template,
                        {'name': booking.name, 'email': booking.email, 'price': booking.price},
                        [booking.email, RECIPIENT_EMAIL]
                    )

                if booking.paid is not None and float(booking.price or 0) > float(booking.paid or 0):
                    diff = round(float(booking.price or 0) - float(booking.paid or 0), 2)
                    email_subject = "Urgent notice for payment discrepancy"
                    email_template = "basecamp/html_email-response-discrepancy.html"
                    self.send_email(
                        email_subject,
                        email_template,
                        {'name': booking.name, 'price': booking.price, 'paid': booking.paid, 'diff': diff},                    
                        [booking.email, booking.email1, RECIPIENT_EMAIL]
                    )

            self.stdout.write(self.style.SUCCESS('No_payment_yet emailed successfully'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send no_payment_yet: {str(e)}'))
        
