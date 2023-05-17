from .models import Post, Inquiry, Payment
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import re
from django.db.models import Q


@receiver(post_save, sender=Post)
def notify_user_post(sender, instance, created, **kwargs):
    if instance.return_flight_number:
        p = Post(name=instance.name, contact=instance.contact, email=instance.email, flight_date=instance.return_flight_date, 
                 flight_number=instance.return_flight_number, flight_time=instance.return_flight_time, pickup_time=instance.return_pickup_time, 
                 direction=instance.return_direction, suburb=instance.suburb, street=instance.street, no_of_passenger=instance.no_of_passenger, 
                 no_of_baggage=instance.no_of_baggage, message=instance.message, return_pickup_time="x",
                 notice=instance.notice, price=instance.price, paid=instance.paid)
        p.save() 
    

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
            [instance.email]
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
                                         'return_direction': instance.return_direction, 'return_flight_date': instance.return_flight_date, 
                                         'return_flight_number': instance.return_flight_number, 'return_flight_time': instance.return_flight_time,
                                         'return_pickup_time': instance.return_pickup_time, 'message': instance.message, 'price': instance.price, 
                                         'notice': instance.notice, 'private_ride': instance.private_ride,})
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "Booking Inquiry - EasyGo",
            text_content,
            '',
            [instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()


# @receiver(post_save, sender=Payment)
# def notify_user_payment(sender, instance, created, **kwargs):      
#     post_name = Post.objects.filter(name__iregex=r'^%s$' % re.escape(instance.item_name)).first()        
#     if post_name: 
#         post_name.paid = instance.gross_amount
#         post_name.save()                

#         if post_name.return_pickup_time == "x":        
#             post_name1 = Post.objects.filter(name__iregex=r'^%s$' % re.escape(instance.item_name))[1]
#             post_name1.paid = instance.gross_amount
#             post_name1.save()
            
#     else:
#         pass
    
#     if not post_name:        
#         post_email = Post.objects.filter(email=instance.payer_email).first()
#         if post_email:
#             post_email.paid = instance.gross_amount
#             post_email.save()            

#             if post_email.return_pickup_time == "x":        
#                 post_email1 = Post.objects.filter(email=instance.payer_email)[1]
#                 post_email1.paid = instance.gross_amount
#                 post_email1.save()
                
#         else:
#             pass
                
#     if not post_name and not post_email:
#         pass


@receiver(post_save, sender=Payment)
def notify_user_payment(sender, instance, created, **kwargs):      
    post_name = Post.objects.filter(Q(name__iregex=r'^%s$' % re.escape(instance.item_name)) | Q(email=instance.payer_email)).first()
    
    if post_name: 
        post_name.paid = instance.gross_amount
        post_name.save() 
        
        html_content = render_to_string("basecamp/html_email-payment-success.html",
                                    {'name': instance.item_name, 'email': instance.payer_email,
                                     'amount': instance.gross_amount })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "PayPal payment - EasyGo",
            text_content,
            '',
            [instance.payer_email, 'info@easygoshuttle.com.au']
        )        
        email.attach_alternative(html_content, "text/html")        
        email.send()               

        if post_name.return_pickup_time == "x":        
            post_name1 = Post.objects.filter(Q(name__iregex=r'^%s$' % re.escape(instance.item_name)) | Q(email=instance.payer_email))[1]
            post_name1.paid = instance.gross_amount
            post_name1.save()
            
    else:
        html_content = render_to_string("basecamp/html_email-noIdentity.html",
                                    {'name': instance.item_name, 'email': instance.payer_email,
                                     'amount': instance.gross_amount })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "PayPal payment - EasyGo",
            text_content,
            '',
            [instance.payer_email, 'info@easygoshuttle.com.au']
        )        
        email.attach_alternative(html_content, "text/html")        
        email.send()