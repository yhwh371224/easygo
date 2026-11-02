import re

from django.db.models import Q

INTL_AIRPORT = "Pickup from Intl Airport"
DOMESTIC_AIRPORT = "Pickup from Domestic Airport"

# Normalize: strip, lowercase, remove all internal spaces so 'Pick up' == 'Pickup'
_INTL_NORM = INTL_AIRPORT.lower().replace(' ', '')
_DOMESTIC_NORM = DOMESTIC_AIRPORT.lower().replace(' ', '')

# direction 없이 start_point 만 공항으로 적힌 예약(p2p 폼/수기 입력)도 비행기 도착이다.
# 공항 호텔·크루즈 터미널은 도착이 아니므로 제외한다. T1=국제선, T2/T3=국내선은 시드니
# 기준(멜번 등은 기사가 만날 곳을 직접 안내해서 터미널 구분이 만남 장소에 영향을 주지 않는다).
# Postgres(운영)와 SQLite(테스트)에서 같이 돌아야 해서 \b 를 쓰지 않는다.
_SOURCE_AIRPORT_RE = (
    r'air ?port'
    r'|(^| )(int|intl|international|domestic)\.? +(term|arrivals)'
    r'|(^| )(t|terminal) ?[123]( |$)'
)
_SOURCE_INTL_RE = r'(^| )(int|intl|international)\.?( |$)|(^| )(t|terminal) ?1( |$)'
_SOURCE_DOMESTIC_RE = r'domestic|(^| )(t|terminal) ?[23]( |$)'
_SOURCE_NOT_AIRPORT_RE = r'otel|travelodge|rydges|ibis|mantra|stamford|moxy|cruise|passenger'

# 공항 도착은 맞는데 'Sydney Airport' 처럼 어느 터미널인지 알 수 없는 건.
# 틀린 터미널의 만남 장소를 안내하면 안 되므로 기본 만남 장소를 자동 배정하지 않는다.
ARRIVAL_UNKNOWN_TERMINAL = 'unknown'


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


def _is_direction_unset(direction):
    """출발지로 판단해도 되는 direction — 공항 방향이 정해지지 않은 건만 해당한다."""
    return not (direction or '').strip() or 'point to point' in direction.lower()


def arrival_type(direction, start_point=None):
    """공항 도착 건이면 'intl'/'domestic'/ARRIVAL_UNKNOWN_TERMINAL, 아니면 None.

    direction 이 우선이고, 비어 있거나 p2p 일 때만 start_point 를 본다.
    """
    if is_intl_pickup(direction):
        return 'intl'
    if is_domestic_pickup(direction):
        return 'domestic'
    if not _is_direction_unset(direction):
        return None
    source = (start_point or '').strip()
    if not re.search(_SOURCE_AIRPORT_RE, source, re.I) or re.search(_SOURCE_NOT_AIRPORT_RE, source, re.I):
        return None
    if re.search(_SOURCE_INTL_RE, source, re.I):
        return 'intl'
    if re.search(_SOURCE_DOMESTIC_RE, source, re.I):
        return 'domestic'
    return ARRIVAL_UNKNOWN_TERMINAL


def airport_arrival_q():
    """공항 도착(픽업) 건 전체를 잡는 느슨한 Q.

    airport_pickup_q()는 iexact라 'Pick up from Intl Airport'처럼 띄어쓰기가
    다른 레거시 값을 놓친다. 리마인더 발송 대상 선정처럼 '하나라도 빠지면
    안 되는' 곳에서는 이쪽을 쓴다(is_airport_pickup의 정규화와 동일 범위).
    direction 이 없어도 start_point 가 공항이면 포함한다(arrival_type 과 동일 기준).
    """
    direction_unset = (
        Q(direction__isnull=True) | Q(direction='')
        | Q(direction__icontains='point to point')
    )
    starts_at_airport = (
        Q(start_point__iregex=_SOURCE_AIRPORT_RE)
        & ~Q(start_point__iregex=_SOURCE_NOT_AIRPORT_RE)
    )
    return Q(direction__iregex=r'pick\s*up from .*airport') | (direction_unset & starts_at_airport)


def intl_pickup_q():
    return Q(direction__iexact=INTL_AIRPORT)


def domestic_pickup_q():
    return Q(direction__iexact=DOMESTIC_AIRPORT)
