from django.core.management.base import BaseCommand
from blog.models import Post
from datetime import datetime, timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from main.settings import RECIPIENT_EMAIL
from retrieve import main 
import re


class Command(BaseCommand):
    help = 'Update reminders and send emails for posts'

    def handle(self, *args, **options):
        my_list = main()  # Call the main function to get the list

        today = datetime.now()
        three_days_later = today + timedelta(days=3)

        for list_email in my_list:      

            posts = Post.objects.filter(email=list_email, flight_date__range=[today, three_days_later])

            for post in posts:
                # print("Post Email:", post.email)

                post.reminder = True
                post.save()
                
                html_content = render_to_string("basecamp/html_email-reminder.html",
                                                {'name': post.name})
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives(
                    "Reminder - EasyGo",
                    text_content,
                    '',
                    [post.email, RECIPIENT_EMAIL]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

        self.stdout.write(self.style.SUCCESS('Successfully updated reminders and sent emails'))

