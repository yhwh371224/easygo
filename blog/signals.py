from .models import Post, Inquiry
from django.shortcuts import render
from django.db.models.signals import post_save
from django.dispatch import receiver

# html email required stuff
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
from time import sleep


@receiver(post_save, sender=Post)
def notify_user_post(sender, instance, created, **kwargs):
    
    if instance.return_flight_number:   
        
        p = Post(name=instance.name, contact=instance.contact, email=instance.email, flight_date=instance.return_flight_date, 
                 flight_number=instance.return_flight_number, flight_time=instance.return_flight_time, pickup_time=instance.return_pickup_time, 
                 direction=instance.return_direction, suburb=instance.suburb, street=instance.street, no_of_passenger=instance.no_of_passenger, 
                 no_of_baggage=instance.no_of_baggage, message=instance.message, notice=instance.notice, price=instance.price, paid=instance.paid)
        
        p.save() 
        
        # user = Post.objects.filter().first()
                        
        # html_content = render_to_string("basecamp/html_email-confirmation-return.html",
        #                                 {'name': user.name, 'contact': user.contact, 'email': user.email,
        #                                  'flight_date': user.flight_date, 'flight_number': user.flight_number,
        #                                  'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
        #                                  'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
        #                                  'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
        #                                  'message': user.message, 'notice': user.notice, 'price': user.price, 'paid': user.paid })

        # text_content = strip_tags(html_content)

        # email = EmailMultiAlternatives(
        #     "Booking confirmation - EasyGo",
        #     text_content,
        #     '',
        #     [instance.email, 'info@easygoshuttle.com.au']
        # )
        # email.attach_alternative(html_content, "text/html")
        
        # email.send()    


@receiver(post_save, sender=Inquiry)
def notify_user_inquiry(sender, instance, created, **kwargs):
    
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
                                         'return_direction': instance.return_direction, 'return_pickup_time': instance.return_pickup_time,
                                         'return_flight_date': instance.return_flight_date, 'return_flight_number': instance.return_flight_number,
                                         'return_flight_time': instance.return_flight_time, 'message': instance.message, 'price': instance.price, 
                                         'notice': instance.notice,})

        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Booking Inquiry - EasyGo",
            text_content,
            '',
            [instance.email, 'info@easygoshuttle.com.au']
        )
        
        email.attach_alternative(html_content, "text/html")
        
        email.send()
    