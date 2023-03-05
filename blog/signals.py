from .models import Post, Inquiry
from django.shortcuts import render
from django.db.models.signals import post_save
from django.dispatch import receiver

# html email required stuff
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail



@receiver(post_save, sender=Post)
def notify_user(sender, instance, created, **kwargs):
    
    if instance.reConfirmed:        
        
        html_content = render_to_string("basecamp/html_email-confirmation.html",
                                        {'name': instance.name, 'contact': instance.contact, 'email': instance.email,
                                         'flight_date': instance.flight_date, 'flight_number': instance.flight_number,
                                         'flight_time': instance.flight_time, 'pickup_time': instance.pickup_time,
                                         'direction': instance.direction, 'street': instance.street, 'suburb': instance.suburb,
                                         'no_of_passenger': instance.no_of_passenger, 'no_of_baggage': instance.no_of_baggage,
                                         'message': instance.message, 'price': instance.price, 'paid': instance.paid })

        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Booking confirmation - EasyGo",
            text_content,
            '',
            [instance.email, 'info@easygoshuttle.com.au']
        )
        email.attach_alternative(html_content, "text/html")
        
        email.send()

    else:
        return None



@receiver(post_save, sender=Inquiry)
def notify_user(sender, instance, created, **kwargs):
    
    if instance.cancelled:        
       
        html_content = render_to_string("basecamp/html_email-cancelled.html",
                                        {'name': instance.name, 'email': instance.email,
                                         })
        
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Booking Inquiry - EasyGo",
            text_content,
            '',
            [instance.email, 'info@easygoshuttle.com.au']
        )
        
        email.attach_alternative(html_content, "text/html")
        
        email.send()

    elif instance.is_confirmed:       
        
        html_content = render_to_string("basecamp/html_email-inquiry-response.html",
                                        {'name': instance.name, 'contact': instance.contact, 'email': instance.email,
                                         'flight_date': instance.flight_date, 'flight_number': instance.flight_number,
                                         'flight_time': instance.flight_time, 'pickup_time': instance.pickup_time,
                                         'direction': instance.direction, 'street': instance.street, 'suburb': instance.suburb,
                                         'no_of_passenger': instance.no_of_passenger, 'no_of_baggage': instance.no_of_baggage,
                                         'message': instance.message, 'price': instance.price})

        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Booking Inquiry - EasyGo",
            text_content,
            '',
            [instance.email, 'info@easygoshuttle.com.au']
        )
        
        email.attach_alternative(html_content, "text/html")
        
        email.send()

    else:
        return None
