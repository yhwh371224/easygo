import re
from django import template

register = template.Library()

_BAGGAGE_FULL_NAMES = {
    'L': 'Large',
    'M': 'Medium',
    'S': 'Small',
    'Baby': 'Baby',
    'Booster': 'Booster',
    'Pram': 'Pram',
    'Ski': 'Ski',
    'Snow': 'Snowboard',
    'Surfboard': 'Surfboard',
    'Bike': 'Bike',
    'Golf': 'Golf',
    'Box': 'Box',
}

_ITEM_PATTERN = re.compile(r'^([A-Za-z]+)(\d+)(\(Oversize\))?$')


@register.filter
def expand_baggage(value):
    """'L12, S3' → 'Large 12 / Small 3'"""
    if not value:
        return value
    parts = [p.strip() for p in str(value).split(',')]
    result = []
    for part in parts:
        m = _ITEM_PATTERN.match(part)
        if m:
            label, qty, oversize = m.group(1), m.group(2), m.group(3)
            full_name = _BAGGAGE_FULL_NAMES.get(label, label)
            item = f"{full_name} {qty}"
            if oversize:
                item += " (Oversize)"
            result.append(item)
        else:
            result.append(part)
    return ' / '.join(result)


@register.filter
def strip_return_marker(value):
    """Remove '===RETURN===' and everything after it from notice."""
    if not value:
        return value
    marker = '===RETURN==='
    idx = str(value).find(marker)
    if idx == -1:
        return value
    return str(value)[:idx].rstrip(' |').strip()


@register.filter
def roundtrip_total(value):
    """Extract round trip total price from notice. Returns string like '500' or None."""
    if not value:
        return None
    m = re.search(r'===RETURN===\s*\(Total Price: \$(\d+(?:\.\d+)?)\)', str(value))
    return m.group(1) if m else None
