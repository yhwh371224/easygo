import logging
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from blog.models import Post, Driver, PhoneMapping
from blog.sms_utils import normalize_phone, format_au_phone

logger = logging.getLogger(__name__)


# =========================
# CONTEXT BUILDER
# =========================
def build_reminder_context(booking, pickup_time_12h, driver):

    customer_phone = normalize_phone(getattr(booking, "contact", None))

    # ✔ FIX: safer proxy detection (not just exists)
    bird_number = None
    if booking.use_proxy and customer_phone:
        if PhoneMapping.objects.filter(from_number=customer_phone).exists():
            bird_number = format_au_phone(settings.BIRD_NUMBER)

    return {
        'booker_name': getattr(booking, "booker_name", None),
        'name': getattr(booking, "name", None),
        'company_name': getattr(booking, "company_name", None),
        'booker_email': getattr(booking, "booker_email", None),
        'email': getattr(booking, "email", None),
        'contact': getattr(booking, "contact", None),
        'pickup_date': getattr(booking, "pickup_date", None),
        'flight_number': getattr(booking, "flight_number", None),
        'flight_time': getattr(booking, "flight_time", None),
        'direction': getattr(booking, "direction", None),
        'pickup_time': pickup_time_12h,
        'start_point': getattr(booking, "start_point", "") or "",
        'end_point': getattr(booking, "end_point", "") or "",
        'street': getattr(booking, "street", None),
        'suburb': getattr(booking, "suburb", None),
        'price': getattr(booking, "price", None),
        'reminder': getattr(booking, "reminder", None),
        'sms_reminder': getattr(booking, "sms_reminder", None),
        'meeting_point': getattr(booking, "meeting_point", None),

        'driver_name': getattr(driver, "driver_name", None) if driver else None,
        'driver_contact': getattr(driver, "driver_contact", None) if driver else None,
        'driver_plate': getattr(driver, "driver_plate", None) if driver else None,
        'driver_car': getattr(driver, "driver_car", None) if driver else None,

        'paid': getattr(booking, "paid", False),
        'cash': getattr(booking, "cash", False),
        'cruise': getattr(booking, "cruise", False),

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

            driver = booking.driver
            if not driver:
                logger.warning(f"No driver for booking {booking.id}")
                continue
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
                getattr(driver, "driver_name", ""),
                booking.name
            )

        # ✔ FIX: batch DB update
        with transaction.atomic():
            if to_update:
                Post.objects.bulk_update(to_update, ["meeting_point"])