# your_app/management/commands/send_apology_emails.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from blog.models import Post

class Command(BaseCommand):
    help = 'Send apology emails to customers created in the last three months'

    def handle(self, *args, **kwargs):
        three_months_ago = timezone.now() - timedelta(days=90)
        customers = Post.objects.filter(created__gte=three_months_ago)

        subject = 'Apology for Recent Email Error'
        message = (
            "Dear Valued Customer,\n\n"
            "I hope this message finds you well.\n\n"
            "I am writing to sincerely apologize for a recent error in our email system. "
            "It has come to our attention that an email may have been sent to you by mistake, "
            "which was not relevant to your current status or interests.\n\n"
            "We understand that your time is valuable and that receiving such an email can be both "
            "confusing and inconvenient. Please rest assured that we are taking all necessary steps to "
            "ensure that this does not happen again in the future. Our team is currently reviewing our "
            "systems and processes to prevent any further issues.\n\n"
            "Your satisfaction is our top priority, and we deeply regret any inconvenience this may have caused. "
            "If you have any questions or concerns, please do not hesitate to contact us \n\n"            
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

