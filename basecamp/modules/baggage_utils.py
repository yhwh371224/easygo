import re


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def add_bag(summary_list, label, qty, oversize=False):
    if qty and qty > 0:
        item = f"{label}{qty}"
        if oversize:
            item += "(Oversize)"
        summary_list.append(item)


def to_bool(value):
    return str(value).lower() in ["true", "1", "on", "yes"]


def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        if value and 'inc' in value.lower():
            return 0.0
        return None


_SPECIAL_KEYS = [
    'baby', 'booster', 'pram',
    'ski', 'snowboard', 'surfboard',
    'bike', 'golf', 'boxes',
]
_NO_OVERSIZE = frozenset({'baby', 'booster', 'pram'})


def parse_special_items(request) -> dict:
    """
    Extract special item counts + oversize flags from POST data.
    Returns a dict suitable for Inquiry.special_items (JSONField).
    Only includes items with qty > 0; oversize flag only when checked.
    """
    result = {}
    for key in _SPECIAL_KEYS:
        qty = to_int(request.POST.get(f'baggage_{key}'))
        if qty > 0:
            result[key] = qty
            if key not in _NO_OVERSIZE and to_bool(request.POST.get(f'{key}_oversize')):
                result[f'{key}_oversize'] = True
    return result


def parse_baggage(request) -> str:
    baggage_summary = []

    large = to_int(request.POST.get('baggage_large'))
    medium = to_int(request.POST.get('baggage_medium'))
    small = to_int(request.POST.get('baggage_small'))
    baby_seat = to_int(request.POST.get('baggage_baby'))
    booster_seat = to_int(request.POST.get('baggage_booster'))
    pram = to_int(request.POST.get('baggage_pram'))
    ski = to_int(request.POST.get('baggage_ski'))
    snowboard = to_int(request.POST.get('baggage_snowboard'))
    golf = to_int(request.POST.get('baggage_golf'))
    bike = to_int(request.POST.get('baggage_bike'))
    boxes = to_int(request.POST.get('baggage_boxes'))
    surfboard = to_int(request.POST.get('baggage_surfboard'))

    ski_os = ski > 0 and to_bool(request.POST.get('ski_oversize'))
    snow_os = snowboard > 0 and to_bool(request.POST.get('snowboard_oversize'))
    surfboard_os = surfboard > 0 and to_bool(request.POST.get('surfboard_oversize'))
    bike_os = bike > 0 and to_bool(request.POST.get('bike_oversize'))
    golf_os = golf > 0 and to_bool(request.POST.get('golf_oversize'))
    box_os = boxes > 0 and to_bool(request.POST.get('boxes_oversize'))

    add_bag(baggage_summary, "L", large)
    add_bag(baggage_summary, "M", medium)
    add_bag(baggage_summary, "S", small)
    add_bag(baggage_summary, "Baby", baby_seat)
    add_bag(baggage_summary, "Booster", booster_seat)
    add_bag(baggage_summary, "Pram", pram)
    add_bag(baggage_summary, "Ski", ski, ski_os)
    add_bag(baggage_summary, "Snow", snowboard, snow_os)
    add_bag(baggage_summary, "Surfboard", surfboard, surfboard_os)
    add_bag(baggage_summary, "Bike", bike, bike_os)
    add_bag(baggage_summary, "Golf", golf, golf_os)
    add_bag(baggage_summary, "Box", boxes, box_os)

    return ", ".join(baggage_summary)


# ── Quick Rebook 카시트 칸 ──
# 다른 예약 폼은 parse_baggage 로 "L2, S1, Baby1, Booster1" 같은 문자열을 만든다.
# Quick Rebook 은 짐을 자유 입력 한 칸으로 받으므로, 카시트만 따로 숫자 칸으로 빼서
# 지난 예약 값을 미리 채워 보여주고 저장할 때 같은 표기로 다시 합친다.
_SEAT_TOKENS = {'baby': 'Baby', 'booster': 'Booster'}


def _split_tokens(baggage):
    return [t.strip() for t in (baggage or '').split(',') if t.strip()]


def split_child_seats(baggage, special_items=None):
    """짐 문자열에서 카시트를 빼낸다 → (나머지 짐 문자열, baby 수, booster 수).

    문자열의 BabyN/BoosterN 표기가 기준이고, 문자열에 없을 때만 special_items 를 쓴다
    (예전 예약 중 special_items 에 카시트가 빠진 건이 있다).
    """
    rest, seats = [], {}
    for token in _split_tokens(baggage):
        m = re.fullmatch(r'(baby|booster)\s*(\d+)', token, re.IGNORECASE)
        if m:
            key = m.group(1).lower()
            seats[key] = seats.get(key, 0) + int(m.group(2))
        else:
            rest.append(token)
    special_items = special_items or {}
    for key in _SEAT_TOKENS:
        if key not in seats:
            seats[key] = to_int(special_items.get(key))
    return ", ".join(rest), seats['baby'], seats['booster']


def join_child_seats(luggage, baby, booster):
    """split_child_seats 의 반대. 카시트는 L/M/S 바로 뒤, 다른 폼과 같은 자리에 넣는다.
    고객이 짐 칸에 BabyN/BoosterN 을 직접 적어도 카시트 칸 값이 기준이다."""
    tokens = [t for t in _split_tokens(luggage)
              if not re.fullmatch(r'(baby|booster)\s*\d+', t, re.IGNORECASE)]
    seats = []
    add_bag(seats, _SEAT_TOKENS['baby'], to_int(baby))
    add_bag(seats, _SEAT_TOKENS['booster'], to_int(booster))
    at = 0
    while at < len(tokens) and re.fullmatch(r'[LMS]\d+', tokens[at]):
        at += 1
    if at == 0:  # 자유 입력("2 bags, golf clubs")이면 뒤에 붙인다.
        at = len(tokens)
    return ", ".join(tokens[:at] + seats + tokens[at:])


# ── 아이 나이 ──
# 카시트를 고른 손님에게만 "Child age(s)" 칸이 보인다. 별도 필드 없이 message 맨 앞에
# 붙여서 관리자·기사 화면, 캘린더에 그대로 보이게 한다.
CHILD_AGES_MAX_LENGTH = 50


def message_with_child_ages(request, message):
    """카시트가 1개 이상이고 나이를 적었으면 message 앞에 'Child age: ...' 줄을 붙인다."""
    ages = ' '.join((request.POST.get('child_ages') or '').split())[:CHILD_AGES_MAX_LENGTH]
    seats = to_int(request.POST.get('baggage_baby')) + to_int(request.POST.get('baggage_booster'))
    if not ages or seats <= 0:
        return message
    line = f"Child age: {ages}"
    return f"{line}\n{message}" if message else line
