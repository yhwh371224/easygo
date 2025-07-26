from django.core.mail import EmailMultiAlternatives
from main.settings import RECIPIENT_EMAIL
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_inquiry_email(instance):
    if instance.is_confirmed:
        html_content = render_to_string("basecamp/html_email-inquiry-response.html", {
            'company_name': instance.company_name, 
            'name': instance.name,
            'contact': instance.contact,
            'email': instance.email,
            'pickup_date': instance.pickup_date,
            'flight_number': instance.flight_number,
            'flight_time': instance.flight_time,
            'pickup_time': instance.pickup_time,
            'direction': instance.direction,
            'street': instance.street,
            'suburb': instance.suburb,
            'start_point': instance.start_point,
            'end_point': instance.end_point, 
            'no_of_passenger': instance.no_of_passenger,
            'no_of_baggage': instance.no_of_baggage,
            'return_direction': instance.return_direction,
            'toll': instance.toll,
            'return_pickup_date': instance.return_pickup_date,
            'return_flight_number': instance.return_flight_number,
            'return_flight_time': instance.return_flight_time,
            'return_pickup_time': instance.return_pickup_time,
            'return_start_point': instance.return_start_point,
            'return_end_point': instance.return_end_point,
            'message': instance.message,
            'price': instance.price,
            'notice': instance.notice,
            'private_ride': instance.private_ride,
        })        

    elif instance.cancelled:
        html_content = render_to_string("basecamp/html_email-cancelled.html", {
            'name': instance.name,
            'email': instance.email,
        })

    elif instance.pending:
        html_content = render_to_string("basecamp/html_email-inquiry-pending.html", {
            'name': instance.name,
            'email': instance.email,
        })

    else:
        return  

    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        "EasyGo Booking Inquiry",
        text_content,
        '',
        [instance.email, RECIPIENT_EMAIL]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()
