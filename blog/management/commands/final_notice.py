import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from main.settings import RECIPIENT_EMAIL


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'Send final notices'

    def handle(self, *args, **options):
        today = date.today()
        tomorrow = today + timedelta(days=1)
        final_notices = Post.objects.filter(pickup_date__range=[today, tomorrow])
        
        for final_notice in final_notices:

            if not final_notice.reminder and not final_notice.cancelled and not final_notice.paid:
                 
                html_content = render_to_string("basecamp/html_email-fnotice.html",
                                                {'name': final_notice.name, 'email': final_notice.email})
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives("Final notice", text_content, '', [final_notice.email, RECIPIENT_EMAIL])
                email.attach_alternative(html_content, "text/html")
                email.send()
            

            

    

                
        
        
