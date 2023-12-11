from __future__ import print_function
from main.settings import RECIPIENT_EMAIL
from .models import Post, Inquiry, Payment
from .tasks import create_event_on_calendar, send_inquiry_confirmed_email, send_inquiry_cancelled_email, notify_user_payment
from basecamp.models import Inquiry_point
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


# Flight return booking
@receiver(post_save, sender=Post)
def notify_user_post(sender, instance, created, **kwargs):
    if instance.return_pickup_time == 'x':
        pass

    elif not instance.calendar_event_id and instance.return_flight_number:
        p = Post(name=instance.name, contact=instance.contact, email=instance.email, company_name=instance.company_name, email1=instance.email1, 
                 flight_date=instance.return_flight_date, flight_number=instance.return_flight_number, flight_time=instance.return_flight_time, 
                 pickup_time=instance.return_pickup_time, direction=instance.return_direction, suburb=instance.suburb, street=instance.street, 
                 no_of_passenger=instance.no_of_passenger, no_of_baggage=instance.no_of_baggage, message=instance.message, return_pickup_time="x",
                 return_flight_date=instance.flight_date, notice=instance.notice, price=instance.price, paid=instance.paid, driver=instance.driver)

        p.save() 
    
    
# Flight inquiry
@receiver(post_save, sender=Inquiry)
def notify_user_inquiry(sender, instance, created, **kwargs):
    if instance.is_confirmed: 
        send_inquiry_confirmed_email.delay(instance_data={
            'company_name': instance.company_name,
            'name': instance.name,
            'contact': instance.contact,
            'email': instance.email,
            'flight_date': instance.flight_date,
            'flight_number': instance.flight_number,
            'flight_time': instance.flight_time,
            'pickup_time': instance.pickup_time,
            'direction': instance.direction,
            'street': instance.street,
            'suburb': instance.suburb,
            'no_of_passenger': instance.no_of_passenger,
            'no_of_baggage': instance.no_of_baggage,
            'return_direction': instance.return_direction,
            'return_flight_date': instance.return_flight_date,
            'return_flight_number': instance.return_flight_number,
            'return_flight_time': instance.return_flight_time,
            'return_pickup_time': instance.return_pickup_time,
            'message': instance.message,
            'price': instance.price,
            'notice': instance.notice,
            'private_ride': instance.private_ride,
        })

    elif instance.cancelled:
        send_inquiry_cancelled_email.delay(instance_data={
            'company_name': instance.company_name,
            'name': instance.name,
            'contact': instance.contact,
            'email': instance.email,
            'flight_date': instance.flight_date,
            'flight_number': instance.flight_number,
            'flight_time': instance.flight_time,
            'pickup_time': instance.pickup_time,
            'direction': instance.direction,
            'street': instance.street,
            'suburb': instance.suburb,
            'no_of_passenger': instance.no_of_passenger,
            'no_of_baggage': instance.no_of_baggage,
            'return_direction': instance.return_direction,
            'return_flight_date': instance.return_flight_date,
            'return_flight_number': instance.return_flight_number,
            'return_flight_time': instance.return_flight_time,
            'return_pickup_time': instance.return_pickup_time,
            'message': instance.message,
            'price': instance.price,
            'notice': instance.notice,
            'private_ride': instance.private_ride,
        })


# Point to point inquiry
@receiver(post_save, sender=Inquiry_point)
def notify_user_inquiry_point(sender, instance, created, **kwargs):
    if instance.is_confirmed:    
        html_content = render_to_string("basecamp/html_email-inquiry-response-p2p.html",
                                        {'name': instance.name, 'contact': instance.contact, 'email': instance.email,
                                         'flight_date': instance.flight_date, 'pickup_time': instance.pickup_time, 'flight_number': instance.flight_number,
                                         'street': instance.street, 'no_of_passenger': instance.no_of_passenger, 'no_of_baggage': instance.no_of_baggage,                                         
                                         'return_flight_date': instance.return_flight_date, 'return_flight_number': instance.return_flight_number, 
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

    elif instance.cancelled:
        html_content = render_to_string("basecamp/html_email-cancelled.html",
                                        {'name': instance.name, 'email': instance.email,
                                         })
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "EasyGo Booking Inquiry",
            text_content,
            '',
            [instance.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    
# PayPal Payment > sending email and saving 
@receiver(post_save, sender=Payment)
def async_notify_user_payment(sender, instance, created, **kwargs):
    # Call the Celery task
    notify_user_payment.delay(instance)  


## google calendar recording 
@receiver(post_save, sender=Post)
def async_create_event_on_calendar(sender, instance, created, **kwargs):
    create_event_on_calendar.delay(instance.id)


                