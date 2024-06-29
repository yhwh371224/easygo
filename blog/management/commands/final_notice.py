import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from utils.email_helper import EmailSender  
from main.settings import RECIPIENT_EMAIL


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Command(BaseCommand):
    help = 'Send final notices using Gmail API'

    def handle(self, *args, **options):
        email_sender = EmailSender()

        tomorrow = date.today() + timedelta(days=1)
        final_notices = Post.objects.filter(pickup_date=tomorrow, reminder=False, cash=False, paid=False)
        
        for final_notice in final_notices:
            html_content = render_to_string("basecamp/html_email-fnotice.html", {'name': final_notice.name, 'email': final_notice.email})            
            subject = "Final notice"
            try:
                email_sender.send_email(subject, [final_notice.email, RECIPIENT_EMAIL], html_content)
                self.stdout.write(self.style.SUCCESS(f"Final notice email sent to {final_notice.email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send email to {final_notice.email}: {e}"))

    

                
        
        
