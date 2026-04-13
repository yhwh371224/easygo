import logging
from datetime import date
from django.core.cache import cache
from blog.models import Post

logger = logging.getLogger(__name__)


def get_default_driver():
    """Return the default (Sam) driver object, cached indefinitely."""
    from blog.models import Driver
    return cache.get_or_set('driver_sam', lambda: Driver.objects.get(driver_name="Sam"), timeout=None)


def assign_default_driver(booking):
    """Assign Sam as default driver if booking has none. Saves and returns driver."""
    if not booking.driver:
        booking.driver = get_default_driver()
        booking.save(update_fields=['driver'])
    return booking.driver


def build_reminder_context(booking, pickup_time_12h, driver):
    """Build the standard template context dict for reminder emails."""
    return {
        'booker_name': booking.booker_name,
        'name': booking.name,
        'company_name': booking.company_name,
        'booker_email': booking.booker_email,
        'email': booking.email,
        'email1': getattr(booking, 'email1', None),
        'contact': getattr(booking, 'contact', None),
        'pickup_date': booking.pickup_date,
        'flight_number': booking.flight_number,
        'flight_time': booking.flight_time,
        'direction': booking.direction,
        'pickup_time': pickup_time_12h,
        'start_point': booking.start_point or "",
        'end_point': booking.end_point or "",
        'street': booking.street,
        'suburb': booking.suburb,
        'price': booking.price,
        'reminder': getattr(booking, 'reminder', False),
        'sms_reminder': getattr(booking, 'sms_reminder', False),
        'meeting_point': booking.meeting_point,
        'driver_name': driver.driver_name,
        'driver_contact': driver.driver_contact,
        'driver_plate': driver.driver_plate,
        'driver_car': driver.driver_car,
        'paid': booking.paid,
        'cash': booking.cash,
        'cruise': getattr(booking, 'cruise', None),
    }


def update_meeting_point_for_arrivals():
    today = date.today()

    rules = [
        {
            "direction": "Pickup from Intl Airport",
            "primary_value": "Public",
            "secondary_value": "Rideshare",
        },
        {
            "direction": "Pickup from Domestic Airport",
            "primary_value": "Express",
            "secondary_value": "Priority",
        },
    ]

    for rule in rules:
        bookings = Post.objects.filter(
            pickup_date=today,
            direction=rule["direction"],
            cancelled=False
        ).select_related("driver").order_by("flight_time")

        driver_first_flag = {}  # 🔥 driver별 상태 관리

        for booking in bookings:
            if booking.meeting_point and booking.meeting_point.strip():
                continue

            # 🔥 driver 없으면 Sam 자동 지정
            driver = assign_default_driver(booking)
            driver_id = driver.id

            if driver_id not in driver_first_flag:
                driver_first_flag[driver_id] = True

            if driver_first_flag[driver_id]:
                booking.meeting_point = rule["primary_value"]
                driver_first_flag[driver_id] = False

                logger.info(
                    f"Set first {rule['primary_value']} for driver {driver.driver_name} "
                    f"- {booking.name} ({booking.flight_time})"
                )
            else:
                booking.meeting_point = rule["secondary_value"]

                logger.info(
                    f"Set {rule['secondary_value']} for driver {driver.driver_name} "
                    f"- {booking.name} ({booking.flight_time})"
                )

            booking.save(update_fields=["meeting_point"])
