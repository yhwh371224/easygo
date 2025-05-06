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
        try: 
            today = date.today()
            tomorrow = today + timedelta(days=1)
            final_notices = Post.objects.filter(pickup_date__range=[today, tomorrow])
            
            for final_notice in final_notices:
                if not final_notice.reminder and not final_notice.cancelled and not final_notice.paid:
                    if final_notice.pickup_date == today:
                        template_name = "basecamp/ftoday.html"
                    else:
                        template_name = "basecamp/html_email-fnotice.html"
                    
                    html_content = render_to_string(template_name, {'name': final_notice.name, 'email': final_notice.email})
                    text_content = strip_tags(html_content)
                    email = EmailMultiAlternatives("Final notice", text_content, '', [final_notice.email, final_notice.email1, RECIPIENT_EMAIL])
                    email.attach_alternative(html_content, "text/html")
                    email.send()

            self.stdout.write(self.style.SUCCESS('Email sent final notice successfully'))

        except Exception as e:            
            self.stdout.write(self.style.ERROR('Failed to send final notices via email'))


            

    

                
        
        
