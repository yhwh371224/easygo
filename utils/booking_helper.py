import logging
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from blog.models import Post, Driver, PhoneMapping
from blog.sms_utils import normalize_phone, format_au_phone
from utils.direction_utils import is_intl_pickup, is_domestic_pickup

logger = logging.getLogger(__name__)


_DIRECTION_ALIASES = {
    "pickup from intl airport": "Pickup from Intl Airport",
    "pickup from domestic airport": "Pickup from Domestic Airport",
    "drop off to intl airport": "Drop off to Intl Airport",
    "drop off to domestic airport": "Drop off to Domestic Airport",
    "cruise transfers or point to point": "Cruise transfers or Point to Point",
}

def normalize_direction(direction):
    """Normalize direction string: collapse spaces, lowercase-compare, return canonical form."""
    if not direction:
        return direction
    key = " ".join(direction.lower().split())
    return _DIRECTION_ALIASES.get(key, direction)


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
        'direction': normalize_direction(getattr(booking, "direction", None)),
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

        'is_intl': is_intl_pickup(getattr(booking, "direction", None)),
        'is_domestic': is_domestic_pickup(getattr(booking, "direction", None)),

        'bird_number': bird_number,

        'post': booking,
    }


# =========================
# MAIN LOGIC (OPTIMIZED)
# =========================
def update_meeting_point_for_arrivals():
    from regions.models import Terminal, TerminalPickupPoint

    today = timezone.localdate()

    DIRECTION_TO_TERMINAL_TYPE = {
        "Pickup from Intl Airport": Terminal.TerminalType.INTL,
        "Pickup from Domestic Airport": Terminal.TerminalType.DOMESTIC,
    }

    from django.db.models import Q as _Q
    bookings = list(
        Post.objects.filter(
            pickup_date=today,
            cancelled=False,
        ).filter(
            _Q(direction__iregex=r'pick\s*up from intl airport') |
            _Q(direction__iregex=r'pick\s*up from domestic airport')
        ).select_related("driver", "region").order_by("flight_time")
    )

    if not bookings:
        return

    _defaults_cache = {}

    def _get_defaults(region_id, terminal_type):
        key = (region_id, terminal_type)
        if key not in _defaults_cache:
            base_qs = TerminalPickupPoint.objects.filter(
                terminal__type=terminal_type,
                terminal__airport__regions=region_id,
            )
            _defaults_cache[key] = (
                base_qs.filter(is_default_point=True).first(),
                base_qs.filter(is_default_second=True).first(),
            )
        return _defaults_cache[key]

    # (driver_id, terminal_type) 키 — 국제선/국내선 별도 카운트
    driver_first_flag = {}
    to_update = []

    for booking in bookings:

        driver = booking.driver
        if not driver:
            logger.warning(f"No driver for booking {booking.id}")
            continue

        terminal_type = DIRECTION_TO_TERMINAL_TYPE.get(normalize_direction(booking.direction))
        if not terminal_type or not booking.region_id:
            continue

        flag_key = (driver.id, terminal_type)
        if flag_key not in driver_first_flag:
            driver_first_flag[flag_key] = True

        if booking.meeting_point or booking.terminal_pickup_point_id:
            # 수동 지정(terminal_pickup_point) 또는 기존 meeting_point → flag 소비 후 스킵
            driver_first_flag[flag_key] = False
            continue

        default_point, default_second = _get_defaults(booking.region_id, terminal_type)

        if driver_first_flag[flag_key]:
            assigned = default_point
            driver_first_flag[flag_key] = False
        else:
            assigned = default_second

        if not assigned:
            logger.warning(
                "No default pickup point for booking %s (region=%s, terminal_type=%s)",
                booking.id, booking.region_id, terminal_type,
            )
            continue

        booking.terminal_pickup_point = assigned
        to_update.append(booking)

        logger.info(
            "Set terminal_pickup_point=%s for %s - %s",
            assigned,
            getattr(driver, "driver_name", ""),
            booking.name,
        )

    with transaction.atomic():
        if to_update:
            Post.objects.bulk_update(to_update, ["terminal_pickup_point"])