from main.settings import RECIPIENT_EMAIL
from basecamp.basecamp_utils import render_email_template
from utils.email import send_html_email
from decimal import Decimal


def _safe_decimal(value):
    """paid is a free-text CharField (may be blank/None/'TBA') — parse defensively."""
    try:
        return Decimal(str(value)) if value not in (None, '', 'TBA') else Decimal(0)
    except Exception:
        return Decimal(0)


def _find_return_leg(instance):
    """Find the sibling Post created by handle_return_trip() for the return leg.

    handle_return_trip() splits a round-trip booking into two Post rows (each
    holding its own half of price/paid) rather than linking them by FK, so we
    match on the fields it sets: same email, return_pickup_time == "x", and
    pickup/return dates swapped relative to this (outbound) instance.
    """
    from blog.models import Post

    if not instance.return_pickup_time or instance.return_pickup_time == 'x':
        return None

    return Post.objects.filter(
        email=instance.email,
        return_pickup_time='x',
        pickup_date=instance.return_pickup_date,
        return_pickup_date=instance.pickup_date,
    ).exclude(pk=instance.pk).order_by('-pk').first()


def send_post_confirmation_email(instance):
    subject = "Booking Confirmation - EasyGo"

    paid_total = instance.paid

    if instance.price not in [None, "TBA", ""]:
        if instance.return_pickup_time:
            return_leg = _find_return_leg(instance)
            if return_leg is not None and return_leg.price not in [None, "TBA", ""]:
                # Sum the two actual split rows rather than assuming an exact
                # 50/50 split (paid amounts can be adjusted per-leg later).
                price = int(Decimal(instance.price) + Decimal(return_leg.price))
                paid_total = _safe_decimal(instance.paid) + _safe_decimal(return_leg.paid)
            else:
                price = int(Decimal(instance.price) * 2)
                paid_total = _safe_decimal(instance.paid) * 2
        else:
            price = int(Decimal(instance.price))
    else:
        price = "TBA"

    raw_discount = str(instance.discount or '').strip()
    try:
        discount_amount = int(Decimal(raw_discount)) if raw_discount else 0
    except Exception:
        discount_amount = 0

    raw_surcharge = str(instance.surcharge or '').strip()
    try:
        surcharge_amount = int(Decimal(raw_surcharge)) if raw_surcharge else 0
    except Exception:
        surcharge_amount = 0

    try:
        final_price = (
            int(Decimal(str(price)) - discount_amount + surcharge_amount)
            if isinstance(price, int) and (discount_amount or surcharge_amount)
            else price
        )
    except Exception:
        final_price = price

    html_content = render_email_template(
        "html_email-confirmation.html",
        {
        'booker_name': instance.booker_name,
        'booker_email': instance.booker_email,
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
        'reminder': instance.reminder,

        # payment
        'price': price,
        'paid': paid_total,
        'cash': instance.cash,
        'prepay': instance.prepay,

        # extra
        'toll': instance.toll,
        'surcharge': surcharge_amount,
        'extra_stop_addresses': instance.extra_stop_addresses or [],
        'same_extra_stop': instance.same_extra_stop,
        'discount': discount_amount,
        'final_price': final_price,
        }
    )

    customer_recipients = [instance.booker_email] if instance.booker_email else list(filter(None, [instance.email, instance.email1]))
    recipients = customer_recipients + [RECIPIENT_EMAIL]
    send_html_email(subject, html_content, recipients)


def send_post_cancelled_email(instance):
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
    
    recipients = [instance.booker_email] if instance.booker_email else list(filter(None, [instance.email, instance.email1]))
    send_html_email("EasyGo Booking Cancelled", html_content, recipients)


def send_missing_direction_email(instance):
    subject = "Booking with Flight Number but Missing Direction"
    template = "html_email-missing-flight-contact.html"

    html_content = render_email_template(template, {
        'booker_name': instance.booker_name,
        'booker_email': instance.booker_email,
        'name': instance.name,
        'email': instance.email,
        'pickup_date': instance.pickup_date,
        'flight_number': instance.flight_number,
        'issues': ['Direction is missing or not specified'],
    })

    send_html_email(subject, html_content, [RECIPIENT_EMAIL])