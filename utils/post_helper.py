from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from main.settings import RECIPIENT_EMAIL
from decimal import Decimal


def send_post_confirmation_email(instance):
    subject = "Booking Confirmation - EasyGo"

    if instance.return_pickup_time:
        price = Decimal(instance.price) * 2
    else:
        price = Decimal(instance.price)

    price = int(price) 

    html_content = render_to_string(
        "basecamp/html_email-confirmation.html",
        {
        'company_name': instance.company_name,
        'name': instance.name,
        'contact': instance.contact,
        'email': instance.email,
        'email1': instance.email1,

        'pickup_date': instance.pickup_date,
        'flight_number': instance.flight_number,
        'flight_time': instance.flight_time,
        'pickup_time': instance.pickup_time,

        'direction': instance.direction,
        'street': instance.street,
        'suburb': instance.suburb,
        'start_point': getattr(instance, 'start_point', ''),
        'end_point': getattr(instance, 'end_point', ''),

        'no_of_passenger': instance.no_of_passenger,
        'no_of_baggage': instance.no_of_baggage,

        # return trip
        'return_direction': instance.return_direction,
        'return_pickup_date': instance.return_pickup_date,
        'return_flight_number': instance.return_flight_number,
        'return_flight_time': instance.return_flight_time,
        'return_pickup_time': instance.return_pickup_time,
        'return_start_point': getattr(instance, 'return_start_point', ''),
        'return_end_point': getattr(instance, 'return_end_point', ''),

        'message': instance.message,
        'notice': instance.notice,

        # payment
        'price': price,
        'paid': instance.paid,
        'cash': instance.cash,
        'prepay': instance.prepay,

        # extra
        'toll': getattr(instance, 'toll', 0),
  
        }
    )

    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject,
        text_content,
        '',  # DEFAULT_FROM_EMAIL 사용
        [instance.email, RECIPIENT_EMAIL],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


def send_post_cancelled_email(instance):
    html_content = render_to_string("basecamp/html_email-cancelled.html", {
        'name': instance.name,
        'email': instance.email,
        'pickup_date': instance.pickup_date or "",
        'pickup_time': instance.pickup_time or "",
        'return_pickup_date': instance.return_pickup_date or "",
        'return_pickup_time': instance.return_pickup_time or "",
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


def send_missing_direction_email(instance):
    subject = "Booking with Flight Number but Missing Direction"
    template = "basecamp/html_email-missing-flight-contact.html"

    html_content = render_to_string(template, {
        'name': instance.name,
        'email': instance.email,
        'pickup_date': instance.pickup_date,
        'flight_number': instance.flight_number,
    })

    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        subject,
        text_content,
        '',
        [RECIPIENT_EMAIL]  
    )
    email.attach_alternative(html_content, "text/html")
    email.send()