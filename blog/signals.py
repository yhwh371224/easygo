from __future__ import print_function

import re

from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from main.settings import RECIPIENT_EMAIL
from .models import Post, Inquiry, Payment, Inquiry_point, Inquiry_cruise
from .tasks import create_event_on_calendar
from django.template.loader import render_to_string
from django.utils.html import strip_tags


# Flight return booking
@receiver(post_save, sender=Post)
def notify_user_post(sender, instance, created, **kwargs):
    if instance.return_pickup_time == 'x' or instance.sent_email:
        pass

    elif not instance.calendar_event_id and instance.return_flight_number:
        p = Post(name=instance.name, contact=instance.contact, email=instance.email, company_name=instance.company_name, email1=instance.email1, 
                 flight_date=instance.return_flight_date, flight_number=instance.return_flight_number, flight_time=instance.return_flight_time, 
                 pickup_time=instance.return_pickup_time, direction=instance.return_direction, suburb=instance.suburb, street=instance.street, 
                 no_of_passenger=instance.no_of_passenger, no_of_baggage=instance.no_of_baggage, message=instance.message, return_pickup_time="x",
                 return_flight_date=instance.flight_date, notice=instance.notice, price=instance.price, paid=instance.paid, driver=instance.driver,)

        p.save() 
    
    
# Flight inquiry
@receiver(post_save, sender=Inquiry)
def notify_user_inquiry(sender, instance, created, **kwargs):
    if instance.is_confirmed:
        html_content = render_to_string("basecamp/html_email-inquiry-response.html",
                                        {'company_name': instance.company_name, 'name': instance.name, 'contact': instance.contact, 
                                         'email': instance.email, 'flight_date': instance.flight_date, 'flight_number': instance.flight_number,
                                         'flight_time': instance.flight_time, 'pickup_time': instance.pickup_time, 'direction': instance.direction, 
                                         'street': instance.street, 'suburb': instance.suburb, 'no_of_passenger': instance.no_of_passenger,
                                         'no_of_baggage': instance.no_of_baggage, 'return_direction': instance.return_direction, 'toll': instance.toll, 
                                         'return_flight_date': instance.return_flight_date, 'return_flight_number': instance.return_flight_number, 
                                         'return_flight_time': instance.return_flight_time, 'return_pickup_time': instance.return_pickup_time, 
                                         'message': instance.message, 'price': instance.price, 'notice': instance.notice, 'private_ride': instance.private_ride,})
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "EasyGo Booking Inquiry",
            text_content,
            '',
            [instance.email, RECIPIENT_EMAIL]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()         

    elif instance.cancelled:
        html_content = render_to_string("basecamp/html_email-cancelled.html",
                                        {'name': instance.name, 'email': instance.email,
                                         })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "EasyGo Booking Inquiry",
            text_content,
            '',
            [RECIPIENT_EMAIL, instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    elif instance.sent_email:
        html_content = render_to_string("basecamp/html_email-inquiry-response-1.html",
                                        {'name': instance.name, 'contact': instance.contact, 'email': instance.email, 'flight_date': instance.flight_date, 
                                        'flight_number': instance.flight_number, 'flight_time': instance.flight_time, 'pickup_time': instance.pickup_time, 'toll': instance.toll, 
                                        'direction': instance.direction, 'street': instance.street, 'suburb': instance.suburb, 'no_of_passenger': instance.no_of_passenger,
                                         'no_of_baggage': instance.no_of_baggage, 'return_direction': instance.return_direction, 'return_flight_date': instance.return_flight_date, 
                                         'return_flight_number': instance.return_flight_number, 'return_flight_time': instance.return_flight_time, 'return_pickup_time': instance.return_pickup_time, 
                                         'message': instance.message, 'price': instance.price, 'notice': instance.notice, 'private_ride': instance.private_ride,})
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "EasyGo Booking Inquiry",
            text_content,
            '',
            [instance.email, RECIPIENT_EMAIL]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()                 


# Point to point inquiry
@receiver(post_save, sender=Inquiry_point)
def notify_user_inquiry_point(sender, instance, created, **kwargs):
    if instance.is_confirmed:    
        html_content = render_to_string("basecamp/html_email-inquiry-response-p2p.html",
                                        {'name': instance.name, 'contact': instance.contact, 'email': instance.email, 'direction': instance.direction, 
                                         'flight_date': instance.flight_date, 'flight_time': instance.flight_time, 'pickup_time': instance.pickup_time, 
                                         'flight_number': instance.flight_number, 'street': instance.street, 'no_of_passenger': instance.no_of_passenger, 
                                         'suburb': instance.suburb, 'no_of_baggage': instance.no_of_baggage, 'return_direction': instance.return_direction, 
                                         'return_flight_date': instance.return_flight_date, 'return_flight_time': instance.return_flight_time, 'toll': instance.toll, 
                                         'return_flight_number': instance.return_flight_number, 'return_pickup_time': instance.return_pickup_time, 
                                         'message': instance.message, 'price': instance.price, 'notice': instance.notice, 'private_ride': instance.private_ride,})
        
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "Booking Inquiry - EasyGo",
            text_content,
            '',
            [RECIPIENT_EMAIL, instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()      

    elif instance.cancelled:
        html_content = render_to_string("basecamp/html_email-cancelled.html",
                                        {'name': instance.name, 'email': instance.email,
                                         })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "EasyGo Booking Inquiry",
            text_content,
            '',
            [RECIPIENT_EMAIL, instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()


# Cruise inquiry
@receiver(post_save, sender=Inquiry_cruise)
def notify_user_inquiry_cruise(sender, instance, created, **kwargs):
    if instance.is_confirmed:    
        html_content = render_to_string("basecamp/html_email-inquiry-response-p2p.html",
                                        {'name': instance.name, 'contact': instance.contact, 'email': instance.email, 'direction': instance.direction, 
                                         'flight_date': instance.flight_date, 'flight_time': instance.flight_time, 'pickup_time': instance.pickup_time, 
                                         'flight_number': instance.flight_number, 'street': instance.street, 'no_of_passenger': instance.no_of_passenger, 
                                         'suburb': instance.suburb, 'no_of_baggage': instance.no_of_baggage, 'return_direction': instance.return_direction, 
                                         'return_flight_date': instance.return_flight_date, 'return_flight_time': instance.return_flight_time, 'toll': instance.toll, 
                                         'return_flight_number': instance.return_flight_number, 'return_pickup_time': instance.return_pickup_time, 
                                         'message': instance.message, 'price': instance.price, 'notice': instance.notice, 'private_ride': instance.private_ride,})
        
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "Booking Inquiry - EasyGo",
            text_content,
            '',
            [RECIPIENT_EMAIL, instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()      

    elif instance.cancelled:
        html_content = render_to_string("basecamp/html_email-cancelled.html",
                                        {'name': instance.name, 'email': instance.email,
                                         })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "EasyGo Booking Inquiry",
            text_content,
            '',
            [RECIPIENT_EMAIL, instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    
# PayPal Payment > sending email and saving 
@receiver(post_save, sender=Payment)
def notify_user_payment(sender, instance, created, **kwargs):
    if instance.item_name is not None:
        post_name = Post.objects.filter(
            Q(name__iregex=r'^%s$' % re.escape(instance.item_name)) | 
            Q(email__iexact=instance.payer_email)
            ).first()

        if post_name:       
            html_content = render_to_string("basecamp/html_email-payment-success.html",
                                        {'name': instance.item_name, 'email': instance.payer_email,
                                         'amount': instance.gross_amount })
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "PayPal payment - EasyGo",
                text_content,
                '',
                [instance.payer_email, RECIPIENT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")        
            email.send()

            checking_message = "short payment"
            post_name.paid = instance.gross_amount            
            post_name.reminder = True
            post_name.discount = ""
            if float(post_name.price) > float(instance.gross_amount):
                post_name.toll = checking_message             
            post_name.save()

            if post_name.return_pickup_time == 'x':                   
                    second_post = Post.objects.filter(email=post_name.email)[1]                    
                    second_post.paid = instance.gross_amount                    
                    second_post.reminder = True
                    second_post.discount = ""
                    if float(post_name.price) > float(instance.gross_amount):
                        second_post.toll = checking_message 
                    second_post.save() 

        else:
            html_content = render_to_string("basecamp/html_email-noIdentity.html",
                                        {'name': instance.item_name, 'email': instance.payer_email,
                                         'amount': instance.gross_amount })
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "PayPal payment - EasyGo",
                text_content,
                '',
                [instance.payer_email, RECIPIENT_EMAIL]
            )  
            email.attach_alternative(html_content, "text/html")        
            email.send()  

    else: pass 


## google calendar recording 
@receiver(post_save, sender=Post)
def async_create_event_on_calendar(sender, instance, created, **kwargs):
    create_event_on_calendar.delay(instance.id)


                