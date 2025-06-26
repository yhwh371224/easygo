from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from main.settings import RECIPIENT_EMAIL


def send_post_cancelled_email(instance):
    html_content = render_to_string("basecamp/html_email-cancelled.html", {
        'name': instance.name,
        'email': instance.email,
    })
    
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        "EasyGo Booking Cancelled",
        text_content,
        '',
        [instance.email, RECIPIENT_EMAIL]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()
