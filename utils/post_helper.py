from main.settings import RECIPIENT_EMAIL
from basecamp.basecamp_utils import render_email_template
from utils.email import send_html_email
from decimal import Decimal


def send_post_confirmation_email(instance):
    subject = "Booking Confirmation - EasyGo"

    if instance.price not in [None, "TBA", ""]:
        if instance.return_pickup_time:
            price = int(Decimal(instance.price) * 2)
        else:
            price = int(Decimal(instance.price))
    else:
        price = "TBA"

    html_content = render_email_template(
        "html_email-confirmation.html",
        {
        'booker_name': instance.booker_name,
        'booking_email': instance.booking_email,
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
        'start_point': instance.start_point,
        'end_point': instance.end_point,

        'no_of_passenger': instance.no_of_passenger,
        'no_of_baggage': instance.no_of_baggage,

        # return trip
        'return_direction': instance.return_direction,
        'return_pickup_date': instance.return_pickup_date,
        'return_flight_number': instance.return_flight_number,
        'return_flight_time': instance.return_flight_time,
        'return_pickup_time': instance.return_pickup_time,
        'return_start_point': instance.return_start_point,
        'return_end_point': instance.return_end_point,

        'message': instance.message,
        'notice': instance.notice,

        # payment
        'price': price,
        'paid': instance.paid,
        'cash': instance.cash,
        'prepay': instance.prepay,

        # extra
        'toll': instance.toll,
        'fuel_surcharge': instance.fuel_surcharge,  
        }
    )

    send_html_email(subject, html_content, [instance.booker_email or instance.email])


def send_post_cancelled_email(instance):
    html_content = render_email_template("html_email-cancelled.html", {
        'booker_name': instance.booker_name,
        'booking_email': instance.booking_email,
        'name': instance.name,
        'email': instance.email,
        'pickup_date': instance.pickup_date,
        'pickup_time': instance.pickup_time,
        'return_pickup_date': instance.return_pickup_date,
        'return_pickup_time': instance.return_pickup_time,
    })
    
    send_html_email("EasyGo Booking Cancelled", html_content, [instance.booker_email or instance.email])


def send_missing_direction_email(instance):
    subject = "Booking with Flight Number but Missing Direction"
    template = "html_email-missing-flight-contact.html"

    html_content = render_email_template(template, {
        'booker_name': instance.booker_name,
        'booking_email': instance.booking_email,
        'name': instance.name,
        'email': instance.email,
        'pickup_date': instance.pickup_date,
        'flight_number': instance.flight_number,
    })

    send_html_email(subject, html_content, [RECIPIENT_EMAIL])