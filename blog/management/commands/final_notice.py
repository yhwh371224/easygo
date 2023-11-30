from django.core.management.base import BaseCommand
from datetime import date, timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from main.settings import RECIPIENT_EMAIL


class Command(BaseCommand):
    help = 'Send final notices'

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        final_notices = Post.objects.filter(flight_date=tomorrow)
        emails_sent = 0

        for final_notice in final_notices:
            if final_notice.cancelled or final_notice.paid:
                continue
            elif not final_notice.reminder:
                html_content = render_to_string("basecamp/html_email-fnotice.html",
                                                {'name': final_notice.name, 'email': final_notice.email})
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives("Final notice", text_content, '', [final_notice.email, RECIPIENT_EMAIL, final_notice.email1])
                email.attach_alternative(html_content, "text/html")
                email.send()
                emails_sent += 1                
        
        self.stdout.write(self.style.SUCCESS(f"{emails_sent} emails sent."))
