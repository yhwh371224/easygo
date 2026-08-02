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


def airport_arrival_q():
    """공항 도착(픽업) 건 전체를 잡는 느슨한 Q.

    airport_pickup_q()는 iexact라 'Pick up from Intl Airport'처럼 띄어쓰기가
    다른 레거시 값을 놓친다. 리마인더 발송 대상 선정처럼 '하나라도 빠지면
    안 되는' 곳에서는 이쪽을 쓴다(is_airport_pickup의 정규화와 동일 범위).
    """
    return Q(direction__iregex=r'pick\s*up from .*airport')


def intl_pickup_q():
    return Q(direction__iexact=INTL_AIRPORT)


def domestic_pickup_q():
    return Q(direction__iexact=DOMESTIC_AIRPORT)
