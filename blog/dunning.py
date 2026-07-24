"""부킹 결제 독촉(dunning) 타임라인 규칙 — 단일 진실 소스(single source of truth).

모든 결제 독촉/자동취소 관련 management command 와 부킹 생성 뷰가 이 모듈의
상수·헬퍼를 공유해서, 사다리 단계·컷오프·유예 규칙이 서로 어긋나지 않게 한다.

설계 요약 (픽업 시각 앵커 + 예약시각 최소유예 바닥):

  단계               Departure            Airport arrival
  ----------------   ------------------   ------------------
  Payment notice     픽업 21일창 진입      동일
  Urgent notice      픽업 72h 전           픽업 96h 전
  Final notice       픽업 48h 전           픽업 72h 전   ("24h 내 미결제 시 취소")
  자동 취소           픽업 24h 전           픽업 48h 전

  · Final notice ↔ 취소 사이 항상 GRACE_HOURS(24h) 유예.
  · 어떤 예약도 (예약시각 + MIN_GRACE_FROM_BOOKING_HOURS) 이전엔 취소하지 않는다
    → 임박 예약이 결제 기회도 없이 잘리는 것 방지.
  · 취소 예정 시각이 픽업을 넘어가는 초임박 예약은 자동취소하지 않는다
    (부킹 생성 시 PREPAY_REQUIRED_LEAD_HOURS 이내면 선결제를 강제하므로,
     정상 흐름에선 이런 건이 미결제 상태로 독촉 풀에 들어오지 않는다).
"""

from datetime import datetime, timedelta

from django.utils import timezone


# ── 취소 컷오프: 픽업 이 시간 전에 자동취소 ──
DEPARTURE_CANCEL_LEAD_HOURS = 24   # 출발(공항 배웅 등) 편
ARRIVAL_CANCEL_LEAD_HOURS = 48     # 공항 도착 편 — 손님이 이동 중(무응답)일 수 있어 더 일찍 컷

# ── final notice → 자동취소 사이 유예 ──
GRACE_HOURS = 24

# ── 예약시각 기준 최소 유예: 방금 예약한 손님을 결제 기회도 없이 취소하지 않음 ──
MIN_GRACE_FROM_BOOKING_HOURS = 12

# ── 부킹 생성 시 이 시간 이내 픽업이면 선결제(prepay) 강제 (방향 무관 단일 기준) ──
PREPAY_REQUIRED_LEAD_HOURS = 24

# ── 사다리 단계별 발송 시점(픽업까지 남은 시간, 이 값 "이하"로 접어들면 발송) ──
URGENT_NOTICE_LEAD_HOURS = {'departure': 72, 'arrival': 96}
FINAL_NOTICE_LEAD_HOURS = {'departure': 48, 'arrival': 72}


def is_airport_arrival(post):
    """공항 도착(=공항에서 손님을 픽업) 건이면 True.

    도착 편은 픽업 직전 손님이 비행 중이라 이메일 무응답이 흔하다 →
    취소 컷오프를 더 일찍 잡는다(ARRIVAL_CANCEL_LEAD_HOURS).
    """
    d = (post.direction or '').lower()
    return 'pickup from' in d and 'airport' in d


def cancel_lead_hours(post):
    """이 부킹의 자동취소 컷오프(픽업 몇 시간 전)."""
    return ARRIVAL_CANCEL_LEAD_HOURS if is_airport_arrival(post) else DEPARTURE_CANCEL_LEAD_HOURS


def combine_pickup(pickup_date, pickup_time):
    """pickup_date + pickup_time("%H:%M") 을 aware datetime 으로 합친다.

    pickup_time 이 없거나 파싱 불가하면 그날 00:00 으로 본다(컷오프를 더 이르게
    잡아 '너무 늦게 취소'하는 위험을 줄이는 보수적 선택).
    반환값은 settings.TIME_ZONE 기준 aware datetime, 날짜 자체가 없으면 None.
    """
    if not pickup_date:
        return None

    t = None
    raw = (pickup_time or '').strip()
    if raw:
        for fmt in ('%H:%M', '%I:%M %p', '%H:%M:%S'):
            try:
                t = datetime.strptime(raw, fmt).time()
                break
            except ValueError:
                continue
    naive = datetime.combine(pickup_date, t) if t else datetime.combine(
        pickup_date, datetime.min.time()
    )
    if timezone.is_naive(naive):
        return timezone.make_aware(naive, timezone.get_default_timezone())
    return naive


def get_pickup_datetime(post):
    """Post 의 pickup_date + pickup_time 을 aware datetime 으로 합친다."""
    return combine_pickup(post.pickup_date, post.pickup_time)


def cancel_deadline(post):
    """이 부킹이 자동취소 대상이 되는 시각.

    = max(픽업 컷오프, 예약시각 + 최소유예)
    픽업 시각을 알 수 없으면 None(자동취소 판단 불가 → 호출측에서 스킵).
    """
    pickup_dt = get_pickup_datetime(post)
    if pickup_dt is None:
        return None
    pickup_cutoff = pickup_dt - timedelta(hours=cancel_lead_hours(post))
    min_grace = post.created + timedelta(hours=MIN_GRACE_FROM_BOOKING_HOURS)
    return max(pickup_cutoff, min_grace)


def is_cancel_eligible(post, now=None):
    """지금 자동취소 대상인지. (미결제 등 다른 필터는 호출측 쿼리에서 처리)

    안전장치: 취소 예정 시각이 픽업을 넘어가면(초임박) 취소하지 않는다.
    """
    now = now or timezone.now()
    deadline = cancel_deadline(post)
    if deadline is None:
        return False
    pickup_dt = get_pickup_datetime(post)
    if pickup_dt is not None and deadline >= pickup_dt:
        # 유예가 픽업을 넘김 → 자동취소 금지(선결제 필수/수동 처리 영역)
        return False
    return now >= deadline


def _lead_key(post):
    return 'arrival' if is_airport_arrival(post) else 'departure'


def hours_until_pickup(post, now=None):
    """픽업까지 남은 시간(시간 단위, float). 픽업 시각 불명이면 None."""
    now = now or timezone.now()
    pickup_dt = get_pickup_datetime(post)
    if pickup_dt is None:
        return None
    return (pickup_dt - now).total_seconds() / 3600.0


def is_urgent_notice_due(post, now=None):
    """Urgent payment notice 발송 시점에 접어들었는지 (dep 72h / arr 96h 이하)."""
    h = hours_until_pickup(post, now)
    return h is not None and 0 < h <= URGENT_NOTICE_LEAD_HOURS[_lead_key(post)]


def is_final_notice_due(post, now=None):
    """Final notice 발송 시점에 접어들었는지 (dep 48h / arr 72h 이하)."""
    h = hours_until_pickup(post, now)
    return h is not None and 0 < h <= FINAL_NOTICE_LEAD_HOURS[_lead_key(post)]


def is_prepay_required_at_booking(pickup_dt, now=None):
    """부킹 생성 시점에 선결제를 강제해야 하는 초임박 예약인지.

    pickup_dt: aware datetime (또는 None → False).
    픽업이 now 로부터 PREPAY_REQUIRED_LEAD_HOURS 이내면 True.
    """
    if pickup_dt is None:
        return False
    now = now or timezone.now()
    return (pickup_dt - now) <= timedelta(hours=PREPAY_REQUIRED_LEAD_HOURS)
