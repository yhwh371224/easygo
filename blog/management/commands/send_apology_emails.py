# your_app/management/commands/send_apology_emails.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from blog.models import Post

class Command(BaseCommand):
    help = 'Send apology emails to customers created in the last three months'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        start_date = today.replace(month=3, day=11)
        end_date = today.replace(month=2, day=11)

        customers = Post.objects.filter(created__range=[end_date, start_date])

        subject = 'Apology for Recent Email Error'
        message = (
            "Dear Valued Customer,\n\n"
            "I hope this message finds you well.\n\n"
            "We recently identified and fixed a system error that caused the loss of booking dates (flight_dates). "
            "We are in the process of recovering the lost information manually, but it is time-consuming, and some booking dates (pickup dates) may not be recoverable.\n\n"
            "We are reaching out individually to request this information. If you have not received such an email, it means we have successfully retrieved your information. "
            "However, if your booking date is approaching and you have not received a reminder notice, please contact us to confirm your details.\n\n"
            "We apologize for any inconvenience this may cause and appreciate your understanding. "
            "We are taking these steps to ensure no mistakes are made and to provide you with the best service possible.\n\n"         
            "Thank you for your understanding and patience.\n\n"
            "Best regards,\n\n"
            "Peter\n"
            "EasyGo Airport Shuttle\n"
            
        )

        for customer in customers:
            send_mail(
                subject,
                message,
                '',
                [customer.email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'Email sent to {customer.email}'))

