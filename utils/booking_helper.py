import logging
from django.utils import timezone

from blog.bird_proxy import get_proxy_number
from blog.models import Post, Driver
from blog.sms_utils import format_au_phone
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
def _get_default_pickup_maps(region_id, terminal_type):
    """해당 지역/터미널 타입의 대표 pickup point에 연결된 모든 map을 반환.
    아직 booking에 terminal_pickup_point가 배정되지 않은 시점(예: 2일전 리마인더)에
    지역별 기본 pickup map(들)을 보여주기 위한 용도.

    update_meeting_point_for_arrivals()가 당일 driver 배정 시 쓰는 것과 동일한
    is_default_point(1순위) → is_default_second(2순위) 어드민 설정을 그대로 따른다."""
    from regions.models import TerminalPickupPoint

    base_qs = TerminalPickupPoint.objects.filter(
        terminal__type=terminal_type,
        terminal__airport__regions=region_id,
    ).prefetch_related("maps")

    point = (
        base_qs.filter(is_default_point=True).first()
        or base_qs.filter(is_default_second=True).first()
    )
    return list(point.maps.all()) if point else []


def _deposit_remaining_balance(booking):
    """디파짓 인보이스가 걸린 예약의 남은 잔액을 계산.
    mirrors blog.blog_utils._net_adjustment — price/paid/discount/toll/surcharge는
    CharField라 blank/None/텍스트값(e.g. "surcharge included")이 섞여 있어 안전 변환 필요."""
    deposit_due = getattr(booking, "deposit_amount_due", None)
    if deposit_due is None:
        return None, None

    def _num(value):
        v = (value or '').strip() if isinstance(value, str) else value
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    price = _num(getattr(booking, "price", None))
    paid = _num(getattr(booking, "paid", None))
    surcharge = _num(getattr(booking, "surcharge", None))
    discount = _num(getattr(booking, "discount", None))
    remaining = round(price + surcharge - discount - paid, 2)
    return float(deposit_due), remaining


def build_reminder_context(booking, pickup_time_12h, driver):
    from regions.models import Terminal

    proxy_number = get_proxy_number(booking, driver)
    bird_number = format_au_phone(proxy_number) if proxy_number else None

    is_intl = is_intl_pickup(getattr(booking, "direction", None))
    is_domestic = is_domestic_pickup(getattr(booking, "direction", None))

    deposit_amount_due, deposit_remaining_balance = _deposit_remaining_balance(booking)

    region_slug = booking.region.slug if booking.region_id else "sydney"

    pickup_maps = []
    if booking.region_id and (is_intl or is_domestic):
        terminal_type = Terminal.TerminalType.INTL if is_intl else Terminal.TerminalType.DOMESTIC
        pickup_maps = _get_default_pickup_maps(booking.region_id, terminal_type)
    if not pickup_maps:
        # 지역에 map 데이터가 없을 때 기존 Sydney 기본 이미지로 폴백
        if is_intl:
            pickup_maps = [{"title": "View Pickup Map", "url": "https://easygo.s3.ap-southeast-2.amazonaws.com/sydmap.svg"}]
        elif is_domestic:
            pickup_maps = [{"title": "Domestic Terminal Pickup Map", "url": "https://easygo.s3.ap-southeast-2.amazonaws.com/t2shuttlebusbay.webp"}]

    return {
        'booker_name': getattr(booking, "booker_name", None),
        'name': getattr(booking, "name", None),
        'company_name': getattr(booking, "company_name", None),
        'booker_email': getattr(booking, "booker_email", None),
        'booker_contact': getattr(booking, "booker_contact", None),
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
        'driver_name': getattr(driver, "driver_name", None) if driver else None,
        'driver_contact': getattr(driver, "driver_contact", None) if driver else None,
        'driver_plate': getattr(driver, "driver_plate", None) if driver else None,
        'driver_car': getattr(driver, "driver_car", None) if driver else None,

        'paid': getattr(booking, "paid", False),
        'cash': getattr(booking, "cash", False),
        'cruise': getattr(booking, "cruise", False),

        'deposit_amount_due': deposit_amount_due,
        'deposit_remaining_balance': deposit_remaining_balance,

        'is_intl': is_intl,
        'is_domestic': is_domestic,

        'bird_number': bird_number,

        'city': booking.region.name if booking.region_id else '',
        'region_slug': region_slug,
        'arrival_guide_url': f"https://easygoshuttle.com.au/{region_slug}/arrival-guide/",
        'pickup_maps': pickup_maps,

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

        if booking.terminal_pickup_point_id:
            # 수동 지정(terminal_pickup_point) → flag 소비 후 스킵
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

    # bulk_update()는 post_save 시그널을 발생시키지 않아 캘린더가 갱신되지 않는다.
    # terminal_pickup_point 변경이 캘린더에 반영되도록 개별 save()로 시그널을 발생시킨다.
    for booking in to_update:
        try:
            booking.save(update_fields=["terminal_pickup_point"])
        except Exception:
            logger.error(
                "Failed to save terminal_pickup_point for booking %s",
                booking.id, exc_info=True,
            )