import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from django.db.models import Q

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'Send final notices'

    def handle(self, *args, **options):
        try:
            tomorrow = date.today() + timedelta(days=1)

            final_notices = Post.objects.filter(
                    pickup_date=tomorrow,
                    cancelled=False,
                    reminder=False,
                    cash=False
                ).filter(
                    Q(paid__isnull=True) | Q(paid__exact="")
                )

            for final_notice in final_notices:
                template_name = "basecamp/html_email-fnotice.html"
                html_content = render_to_string(template_name, {
                    'name': final_notice.name,
                    'email': final_notice.email
                })
                text_content = strip_tags(html_content)

                email = EmailMultiAlternatives(
                    "Final notice",
                    text_content,
                    '',
                    [final_notice.email, final_notice.email1, RECIPIENT_EMAIL]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

                final_notice.cancelled = True
                final_notice.save()

            self.stdout.write(self.style.SUCCESS('Final notices sent and marked as cancelled.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send final notices: {str(e)}'))


            

    

                
        
        
