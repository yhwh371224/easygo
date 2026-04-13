from main.settings import RECIPIENT_EMAIL
from basecamp.basecamp_utils import render_email_template
from utils.email import send_html_email


def send_inquiry_email(instance):
    if instance.is_confirmed:
        html_content = render_email_template("html_email-inquiry-response.html", {
            'booker_name': instance.booker_name,
            'booker_email': instance.booker_email,
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
            'fuel_surcharge': instance.fuel_surcharge,
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
        html_content = render_email_template("html_email-cancelled.html", {
            'booker_name': instance.booker_name,
            'booker_email': instance.booker_email,
            'name': instance.name,
            'email': instance.email,
            'pickup_date': instance.pickup_date,
            'pickup_time': instance.pickup_time,
            'return_pickup_date': instance.return_pickup_date,
            'return_pickup_time': instance.return_pickup_time,
        })

    elif instance.pending:
        html_content = render_email_template("html_email-inquiry-pending.html", {
            'booker_name': instance.booker_name,
            'booker_email': instance.booker_email,
            'name': instance.name,
            'email': instance.email,
            'pickup_date': instance.pickup_date,
            'pickup_time': instance.pickup_time,
            'return_pickup_date': instance.return_pickup_date,
            'return_pickup_time': instance.return_pickup_time,
        })

    else:
        return False

    send_html_email("EasyGo Booking Inquiry", html_content, [instance.booker_email or instance.email])
    return True
