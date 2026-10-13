import logging
from django.utils import timezone

from blog.bird_proxy import get_proxy_number
from blog.models import Post, Driver
from blog.sms_utils import format_au_phone
from utils.direction_utils import is_intl_pickup, is_domestic_pickup

# 우버로 대신 보내는 건에 배정하는 가상 드라이버. 도착 픽업이면 손님에게 이름·번호만
# 알려주고, 만남 장소는 짐을 찾은 뒤 그 번호로 연락해 묻도록 안내한다.
UGO_DRIVER_NAME = 'ugo'


def is_ugo_driver(driver):
    return bool(driver) and (driver.driver_name or '').strip().lower() == UGO_DRIVER_NAME

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


# 시드니 국제선(SYD T1) 도착 픽업은 드라이버/순번과 상관없이 무조건 Public Pickup 으로 배정한다.
# 기존 1순위(is_default_point)/2순위(is_default_second)·수동 지정 로직은 다른 지역이 계속 쓰므로 그대로 두고,
# 시드니 국제선만 그 앞에서 가로챈다. 되돌리려면 아래 sydney_public 분기 두 곳만 주석처리하면 된다.
SYDNEY_INTL_AIRPORT_CODE = 'SYD'
SYDNEY_INTL_PICKUP_POINT_NAME = 'Public Pickup'

# 공항 사정상 정해진 만남 장소가 없고 드라이버가 그때그때 만날 곳을 알려주는 지역.
# 이 지역 도착 건은 기본 만남 장소를 자동 배정하지 않고, 메일에도 "드라이버에게 연락해 지시를
# 받고, 연락이 안 되면 이메일" 안내만 넣는다. (어드민에서 수동 지정한 장소는 그대로 존중)
DRIVER_DIRECTED_REGION_SLUGS = {'melbourne'}


def is_driver_directed_region(region):
    return bool(region) and region.slug in DRIVER_DIRECTED_REGION_SLUGS


def _sydney_intl_public_pickup(region_id, terminal_type):
    """region 이 SYD 공항에 연결된 국제선 도착이면 Public Pickup 포인트, 아니면 None."""
    from regions.models import Terminal, TerminalPickupPoint

    if terminal_type != Terminal.TerminalType.INTL:
        return None
    return TerminalPickupPoint.objects.filter(
        terminal__type=terminal_type,
        terminal__airport__code=SYDNEY_INTL_AIRPORT_CODE,
        terminal__airport__regions=region_id,
        name__iexact=SYDNEY_INTL_PICKUP_POINT_NAME,
    ).first()


# =========================
# CONTEXT BUILDER
# =========================
def _get_default_pickup_point(region_id, terminal_type):
    """해당 지역/터미널 타입의 대표 pickup point.
    아직 booking에 terminal_pickup_point가 배정되지 않은 시점(예: 2일전 리마인더, 당일 배정 전)에
    지역 기본 만남 장소(이름·안내문·지도)를 보여주기 위한 용도.

    update_meeting_point_for_arrivals()가 당일 driver 배정 시 쓰는 것과 동일한
    is_default_point(1순위) → is_default_second(2순위) 어드민 설정을 그대로 따른다."""
    from regions.models import TerminalPickupPoint

    sydney_public = _sydney_intl_public_pickup(region_id, terminal_type)
    if sydney_public:
        return sydney_public

    base_qs = TerminalPickupPoint.objects.filter(
        terminal__type=terminal_type,
        terminal__airport__regions=region_id,
    )
    return (
        base_qs.filter(is_default_point=True).first()
        or base_qs.filter(is_default_second=True).first()
    )


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

    driver_directs_meeting = (is_intl or is_domestic) and is_driver_directed_region(booking.region)

    default_pickup_point = None
    pickup_maps = []
    if booking.region_id and (is_intl or is_domestic) and not driver_directs_meeting:
        terminal_type = Terminal.TerminalType.INTL if is_intl else Terminal.TerminalType.DOMESTIC
        default_pickup_point = _get_default_pickup_point(booking.region_id, terminal_type)
        if default_pickup_point:
            pickup_maps = list(default_pickup_point.maps.all())
    if not pickup_maps and region_slug == "sydney":
        # 시드니에 map 데이터가 없을 때만 기존 Sydney 기본 이미지로 폴백.
        # 다른 지역에 시드니 지도를 보내면 안 되므로 그 지역은 지도 없이 나간다.
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
        'no_email_reminder': getattr(booking, "no_email_reminder", None),
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
        'is_ugo_arrival': is_ugo_driver(driver) and (is_intl or is_domestic),

        'city': booking.region.name if booking.region_id else '',
        'region_slug': region_slug,
        'arrival_guide_url': f"https://easygoshuttle.com.au/{region_slug}/arrival-guide/",
        'pickup_maps': pickup_maps,
        'default_pickup_point': default_pickup_point,
        'driver_directs_meeting': driver_directs_meeting,

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
    _sydney_public_cache = {}

    def _get_sydney_public(region_id, terminal_type):
        key = (region_id, terminal_type)
        if key not in _sydney_public_cache:
            _sydney_public_cache[key] = _sydney_intl_public_pickup(region_id, terminal_type)
        return _sydney_public_cache[key]

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

        # Ugo 는 손님이 짐 찾은 뒤 전화로 만날 곳을 정한다 — 기본 만남 장소를 넣지 않는다.
        if is_ugo_driver(driver):
            continue

        terminal_type = DIRECTION_TO_TERMINAL_TYPE.get(normalize_direction(booking.direction))
        if not terminal_type or not booking.region_id:
            continue

        # 멜번 등: 드라이버가 만날 곳을 직접 알려준다 — 기본 만남 장소를 넣지 않는다.
        if is_driver_directed_region(booking.region):
            continue

        # 시드니 국제선: 수동 지정 여부·드라이버 순번 무시하고 무조건 Public Pickup.
        sydney_public = _get_sydney_public(booking.region_id, terminal_type)
        if sydney_public:
            if booking.terminal_pickup_point_id != sydney_public.id:
                booking.terminal_pickup_point = sydney_public
                to_update.append(booking)
                logger.info(
                    "Set terminal_pickup_point=%s for %s - %s (Sydney intl forced)",
                    sydney_public,
                    getattr(driver, "driver_name", ""),
                    booking.name,
                )
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