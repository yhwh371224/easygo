from django.db.models import Q

INTL_AIRPORT = "Pickup from Intl Airport"
DOMESTIC_AIRPORT = "Pickup from Domestic Airport"

# Normalize: strip, lowercase, remove all internal spaces so 'Pick up' == 'Pickup'
_INTL_NORM = INTL_AIRPORT.lower().replace(' ', '')
_DOMESTIC_NORM = DOMESTIC_AIRPORT.lower().replace(' ', '')


def _normalize(direction):
    return (direction or '').strip().lower().replace(' ', '')


def is_intl_pickup(direction):
    return _normalize(direction) == _INTL_NORM


def is_domestic_pickup(direction):
    return _normalize(direction) == _DOMESTIC_NORM


def is_airport_pickup(direction):
    return _normalize(direction) in {_INTL_NORM, _DOMESTIC_NORM}


def airport_pickup_q():
    return Q(direction__iexact=INTL_AIRPORT) | Q(direction__iexact=DOMESTIC_AIRPORT)


def intl_pickup_q():
    return Q(direction__iexact=INTL_AIRPORT)


def domestic_pickup_q():
    return Q(direction__iexact=DOMESTIC_AIRPORT)
