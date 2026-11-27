"""EasyGo 회사 사실 정보 — schema(JSON-LD), About 페이지, /llms.txt 가 같이 쓴다.

AI 검색(ChatGPT·Perplexity·Google AI)은 "이 회사가 실제로 있고 믿을 만한가"를 이런
사실로 판단한다 (2026-11-28 점검). 한 곳에 모아 둬서 페이지마다 값이 어긋나지 않게 한다.

None / 빈 값은 화면과 schema 에서 빠진다 — 확인된 값만 채운다.
"""

from django.core.cache import cache

NAME = 'EasyGo Airport Shuttle'
URL = 'https://easygoshuttle.com.au'
STREET = '119 Willoughby Road'
LOCALITY = 'Crows Nest'
REGION = 'NSW'
POSTCODE = '2065'
# 119 Willoughby Rd, Crows Nest (예전 schema 는 시드니 CBD 기본 좌표였다)
LATITUDE = '-33.8259'
LONGITUDE = '151.2017'
OPENING_HOURS = 'Mo-Su 00:00-23:59'   # 본문의 "24/7" 과 맞춘다

# ── 오너 확인이 필요한 값 (확인 전에는 비워 둔다) ─────────────────────────
FOUNDED_YEAR = None             # 실제 사업 시작 연도 (DB 기록은 2023 부터)
P2P_AUTHORISATION = ''          # NSW Point to Point Transport Commission 인가 번호
ABN = ''                        # 공개해도 된다고 하면 채운다

# 다른 사이트의 EasyGo 프로필 — schema sameAs. AI 가 같은 회사로 묶는 근거.
SAME_AS = [
    'https://www.google.com/maps/place/?q=place_id:ChIJgScpoZGnEmsRo1T_fWF7Ato',
    # 'https://www.tripadvisor.com.au/...d27753160...',   # 크롬으로 정확한 주소 확인 후
    # 'https://www.facebook.com/easygoshuttle',           # 계정이 살아 있는지 확인 후
]

STATS_CACHE_KEY = 'business_facts:stats'
STATS_CACHE_SECONDS = 60 * 60 * 24


def stats():
    """예약 DB 에서 계산한 실적 숫자 (하루 캐시). 지어낸 숫자를 쓰지 않으려고 직접 센다.

    trips: 지난 날짜의 취소 안 된 운행 수 (왕복은 편도 두 번)
    customers: 이메일 기준 손님 수, repeat_pct: 두 번 이상 예약한 손님 비율
    group_pct: 5명 이상 예약 비율
    """
    cached = cache.get(STATS_CACHE_KEY)
    if cached is not None:
        return cached
    from collections import Counter
    from django.utils import timezone
    from blog.models import Post

    done = Post.objects.filter(cancelled=False, pickup_date__lt=timezone.localdate())
    bookings = done.exclude(return_pickup_time='x')
    emails = Counter(e.strip().lower() for e in bookings.exclude(email__isnull=True)
                     .exclude(email='').values_list('email', flat=True))
    pax = [int(p) for p in bookings.values_list('no_of_passenger', flat=True) if str(p).strip().isdigit()]
    first = done.order_by('pickup_date').values_list('pickup_date', flat=True).first()
    result = {
        'trips': done.count(),
        'customers': len(emails),
        'repeat_pct': round(100 * sum(1 for c in emails.values() if c > 1) / len(emails)) if emails else 0,
        'group_pct': round(100 * sum(1 for p in pax if p >= 5) / len(pax)) if pax else 0,
        'since_year': first.year if first else None,
        'as_of': timezone.localdate(),
    }
    cache.set(STATS_CACHE_KEY, result, STATS_CACHE_SECONDS)
    return result


def rounded_down(n, step=100):
    """5,323 → '5,300+' — 매일 바뀌는 숫자를 그대로 쓰지 않고 보수적으로 내린다."""
    if n < step:
        return str(n)
    return f'{(n // step) * step:,}+'


def context(request):
    """템플릿용 context processor: {{ facts.* }}"""
    return {'facts': {
        'name': NAME, 'url': URL, 'street': STREET, 'locality': LOCALITY, 'region': REGION,
        'postcode': POSTCODE, 'latitude': LATITUDE, 'longitude': LONGITUDE,
        'opening_hours': OPENING_HOURS, 'founded_year': FOUNDED_YEAR,
        'p2p_authorisation': P2P_AUTHORISATION, 'abn': ABN, 'same_as': SAME_AS,
    }}


def llms_txt(request):
    """/llms.txt — AI 가 EasyGo 를 한눈에 이해하도록 쓴 요약 (llmstxt.org 형식)."""
    from django.http import HttpResponse
    from easygo_review.review_stats import get_review_stats

    n = stats()
    reviews = get_review_stats()
    lines = [
        f'# {NAME}',
        '',
        '> Private airport and cruise transfers in Sydney, Melbourne and the Gold Coast, '
        'in 7–13 seater vehicles for individuals, families and groups. Fixed price confirmed '
        'before travel, flight tracking, door-to-door.',
        '',
        '## Key facts',
        f'- Address: {STREET}, {LOCALITY} {REGION} {POSTCODE}, Australia',
        f'- Completed trips: {rounded_down(n["trips"])} (from our booking records, {n["as_of"]:%B %Y})',
        f'- Customers: {rounded_down(n["customers"])}; {n["repeat_pct"]}% have booked more than once',
        f'- {n["group_pct"]}% of bookings are groups of 5 or more passengers',
    ]
    if reviews.get('google_rating') and reviews.get('google_review_count'):
        lines.append(f'- Google rating: {reviews["google_rating"]} from {reviews["google_review_count"]} reviews')
    if FOUNDED_YEAR:
        lines.append(f'- Operating since: {FOUNDED_YEAR}')
    if ABN:
        lines.append(f'- ABN: {ABN}')
    if P2P_AUTHORISATION:
        lines.append(f'- NSW Point to Point Transport Commission authorisation: {P2P_AUTHORISATION}')
    lines += [
        '- Waiting: up to 80 minutes after an international landing and 50 minutes after a domestic landing at no extra charge',
        '- Child seats (baby capsule, baby seat, booster) available on request',
        '- Payment: card (Stripe), PayPal, PayID or cash to driver',
        '',
        '## Main pages',
        f'- [Sydney airport transfers]({URL}/): home page, prices and booking',
        f'- [Melbourne airport transfers]({URL}/melbourne/)',
        f'- [Gold Coast airport transfers]({URL}/gold-coast/)',
        f'- [Sydney airport meeting points]({URL}/meeting_point/): where the driver meets you at each terminal',
        f'- [Customer reviews]({URL}/easygo_review/)',
        f'- [About EasyGo]({URL}/about_us/)',
        f'- [Booking information and FAQ]({URL}/information/)',
        '',
        '## Contact',
        f'- Website: {URL}',
        '- Email: info@easygoshuttle.com.au',
    ]
    return HttpResponse('\n'.join(lines) + '\n', content_type='text/plain; charset=utf-8')
