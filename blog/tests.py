from .models import Post
from datetime import datetime, timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from main.settings import RECIPIENT_EMAIL
from retrieve import main as gmail_main


my_list = gmail_main()  # Call the main function to get the list

today = datetime.now()
three_days_later = today + timedelta(days=3)


def update_reminder():
    for list_email in my_list:
        posts = Post.objects.filter(email=list_email)
        
        for post in posts: 
            post.reminder = True
            post.save()

            # html_content = render_to_string("basecamp/html_email-reminder.html",
            #                                 {'name': post.name})
            # text_content = strip_tags(html_content)
            # email = EmailMultiAlternatives(
            #     "Reminder - EasyGo",
            #     text_content,
            #     '',
            #     [post.email, RECIPIENT_EMAIL]
            # )
            # email.attach_alternative(html_content, "text/html")
            # email.send()

update_reminder()
    




