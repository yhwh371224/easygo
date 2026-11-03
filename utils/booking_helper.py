import logging
from django.utils import timezone

from blog.bird_proxy import get_proxy_number
from blog.models import Post, Driver
from blog.sms_utils import format_au_phone
from utils.direction_utils import ARRIVAL_UNKNOWN_TERMINAL, airport_arrival_q, arrival_type

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


def reverse_direction(direction):
    """왕복의 돌아오는 편 방향. 공항 픽업 <-> 드롭오프만 뒤집고 크루즈 등은 그대로 둔다."""
    direction = normalize_direction(direction) or ''
    if direction.startswith('Pickup from '):
        return direction.replace('Pickup from ', 'Drop off to ', 1)
    if direction.startswith('Drop off to '):
        return direction.replace('Drop off to ', 'Pickup from ', 1)
    return direction


# 공항 사정상 정해진 만남 장소가 없고 드라이버가 그때그때 만날 곳을 알려주는 지역.
# 이 지역 도착 건은 기본 만남 장소를 자동 배정하지 않고, 메일에도 "드라이버에게 연락해 지시를
# 받고, 연락이 안 되면 이메일" 안내만 넣는다. (어드민에서 수동 지정한 장소는 그대로 존중)
DRIVER_DIRECTED_REGION_SLUGS = {'melbourne'}


def region_arrival_point(region):
    """지역 전체 도착 건의 고정 만남 장소(Region.arrival_meeting_point). 없으면 None."""
    if not region or not getattr(region, 'arrival_meeting_point_id', None):
        return None
    return region.arrival_meeting_point


def is_driver_directed_region(region):
    # 지역 고정 만남 장소가 있으면 그 안내가 우선한다 — '기사가 알려줌' 문구를 쓰지 않는다.
    if region_arrival_point(region):
        return False
    return bool(region) and region.slug in DRIVER_DIRECTED_REGION_SLUGS


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

    arrival = arrival_type(getattr(booking, "direction", None), getattr(booking, "start_point", None))
    # 'Sydney Airport' 처럼 터미널을 모르는 건은 어드민이 지정한 만남 장소의 터미널을 따른다.
    manual_point = getattr(booking, "terminal_pickup_point", None)
    if arrival == ARRIVAL_UNKNOWN_TERMINAL and manual_point:
        arrival = 'intl' if manual_point.terminal.type == Terminal.TerminalType.INTL else 'domestic'
    is_intl = arrival == 'intl'
    is_domestic = arrival == 'domestic'

    deposit_amount_due, deposit_remaining_balance = _deposit_remaining_balance(booking)

    region_slug = booking.region.slug if booking.region_id else "sydney"

    driver_directs_meeting = (is_intl or is_domestic) and is_driver_directed_region(booking.region)

    default_pickup_point = None
    pickup_maps = []
    fixed_point = region_arrival_point(booking.region) if (is_intl or is_domestic) else None
    if fixed_point:
        # 지역 고정 만남 장소 — 국제선·국내선 구분 없이 같은 곳.
        default_pickup_point = fixed_point
        pickup_maps = list(fixed_point.maps.all())
    elif booking.region_id and (is_intl or is_domestic) and not driver_directs_meeting:
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
        # 도착 건 전용 — 공용 템플릿이라 출발 메일까지 문구가 빠지지 않게 여기서 막는다.
        'hide_arrival_pickup_time': (is_intl or is_domestic) and getattr(booking, "hide_arrival_pickup_time", False),
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
        # 국내선 손님도 국제선 터미널에서 만날 수 있으므로 템플릿이 터미널 이름을 그대로 보여준다.
        'region_fixed_point': bool(fixed_point),

        'post': booking,
    }


# =========================
# MAIN LOGIC (OPTIMIZED)
# =========================
def update_meeting_point_for_arrivals():
    from regions.models import Terminal, TerminalPickupPoint

    today = timezone.localdate()

    ARRIVAL_TO_TERMINAL_TYPE = {
        'intl': Terminal.TerminalType.INTL,
        'domestic': Terminal.TerminalType.DOMESTIC,
    }

    bookings = list(
        Post.objects.filter(
            pickup_date=today,
            cancelled=False,
        ).filter(
            airport_arrival_q()
        ).select_related("driver", "region__arrival_meeting_point").order_by("flight_time")
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

        # Ugo 는 손님이 짐 찾은 뒤 전화로 만날 곳을 정한다 — 기본 만남 장소를 넣지 않는다.
        if is_ugo_driver(driver):
            continue

        # 지역 고정 만남 장소(예: Melbourne T2 Groups & Charters): 기사·터미널과 상관없이
        # 모든 도착 건에 같은 곳. 수동 지정한 장소는 건드리지 않는다.
        fixed_point = region_arrival_point(booking.region)
        if fixed_point:
            if not booking.terminal_pickup_point_id:
                booking.terminal_pickup_point = fixed_point
                to_update.append(booking)
                logger.info("Set terminal_pickup_point=%s (region fixed) for %s", fixed_point, booking.name)
            continue

        if not driver:
            logger.warning(f"No driver for booking {booking.id}")
            continue

        terminal_type = ARRIVAL_TO_TERMINAL_TYPE.get(arrival_type(booking.direction, booking.start_point))
        if not terminal_type or not booking.region_id:
            continue

        # 멜번 등: 드라이버가 만날 곳을 직접 알려준다 — 기본 만남 장소를 넣지 않는다.
        if is_driver_directed_region(booking.region):
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