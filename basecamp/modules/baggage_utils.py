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
