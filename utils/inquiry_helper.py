from django.core.mail import EmailMultiAlternatives
from main.settings import RECIPIENT_EMAIL
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_inquiry_email(instance):
    if instance.is_confirmed:
        html_content = render_to_string("basecamp/html_email-inquiry-response.html", {
            'company_name': instance.company_name or "",
            'name': instance.name or "",
            'contact': instance.contact or "",
            'email': instance.email or "",
            'pickup_date': instance.pickup_date or "",
            'flight_number': instance.flight_number or "",
            'flight_time': instance.flight_time or "",
            'pickup_time': instance.pickup_time or "",
            'direction': instance.direction or "",
            'street': instance.street or "",
            'suburb': instance.suburb or "",
            'start_point': instance.start_point or "",
            'end_point': instance.end_point or "",
            'no_of_passenger': instance.no_of_passenger or "",
            'no_of_baggage': instance.no_of_baggage or "",
            'return_direction': instance.return_direction or "",
            'toll': instance.toll or "",
            'return_pickup_date': instance.return_pickup_date or "",
            'return_flight_number': instance.return_flight_number or "",
            'return_flight_time': instance.return_flight_time or "",
            'return_pickup_time': instance.return_pickup_time or "",
            'return_start_point': instance.return_start_point or "",
            'return_end_point': instance.return_end_point or "",
            'message': instance.message or "",
            'price': instance.price or "",
            'notice': instance.notice or "",
            'private_ride': instance.private_ride or "",
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
