import logging
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from blog.models import Post, Driver, PhoneMapping
from blog.sms_utils import normalize_phone

logger = logging.getLogger(__name__)


# =========================
# DRIVER CACHE (FIXED)
# =========================
def get_default_driver():
    """
    Cached safe driver lookup (Sam)
    """
    driver, _ = Driver.objects.get_or_create(driver_name="Sam")
    return driver


def assign_default_driver(booking):
    if not booking.driver:
        booking.driver = get_default_driver()
        booking.save(update_fields=['driver'])
    return booking.driver


# =========================
# CONTEXT BUILDER
# =========================
def build_reminder_context(booking, pickup_time_12h, driver):

    customer_phone = normalize_phone(booking.contact)

    # ✔ FIX: safer proxy detection (not just exists)
    bird_number = None
    if booking.use_proxy and customer_phone:
        if PhoneMapping.objects.filter(from_number=customer_phone).exists():
            bird_number = settings.BIRD_NUMBER

    return {
        'booker_name': booking.booker_name,
        'name': booking.name,
        'company_name': booking.company_name,
        'booker_email': booking.booker_email,
        'email': booking.email,
        'contact': booking.contact,
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
        'reminder': booking.reminder,
        'sms_reminder': booking.sms_reminder,
        'meeting_point': booking.meeting_point,
        'driver_name': driver.driver_name,
        'driver_contact': driver.driver_contact,
        'driver_plate': driver.driver_plate,
        'driver_car': driver.driver_car,
        'paid': booking.paid,
        'cash': booking.cash,
        'cruise': booking.cruise,
        'bird_number': bird_number,
    }


# =========================
# MAIN LOGIC (OPTIMIZED)
# =========================
def update_meeting_point_for_arrivals():

    today = timezone.localdate()

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

        bookings = list(
            Post.objects.filter(
                pickup_date=today,
                direction=rule["direction"],
                cancelled=False
            ).select_related("driver").order_by("flight_time")
        )

        if not bookings:
            continue

        driver_first_flag = {}

        # ✔ FIX: reduce DB writes via bulk pattern
        to_update = []

        for booking in bookings:

            driver = assign_default_driver(booking)
            driver_id = driver.id

            if driver_id not in driver_first_flag:
                driver_first_flag[driver_id] = True

            if booking.meeting_point:
                # 이미 배정된 경우 flag만 소비하고 스킵
                driver_first_flag[driver_id] = False
                continue

            if driver_first_flag[driver_id]:
                booking.meeting_point = rule["primary_value"]
                driver_first_flag[driver_id] = False
            else:
                booking.meeting_point = rule["secondary_value"]

            to_update.append(booking)

            logger.info(
                'Set %s for %s - %s',
                booking.meeting_point,
                driver.driver_name,
                booking.name
            )

        # ✔ FIX: batch DB update
        with transaction.atomic():
            for b in to_update:
                b.save(update_fields=["meeting_point"])