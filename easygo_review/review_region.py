"""리뷰를 남긴 손님이 사는 서버브(Hornsby, Ryde ...) 찾기.

리뷰(easygo_review.Post)에는 예약과 이어진 필드가 없다. 리뷰 이름은 예약
(blog.Post)의 손님 이름을 그대로 쓰므로(PostCreate) 같은 이름의 예약에서 서버브를
가져온다. 새 DB 필드 없이 화면을 그릴 때 계산한다. 못 찾으면 표시하지 않는다.

호텔·크루즈 터미널·공항은 사는 곳이 아니라서 건너뛴다 ("Hotels In CBD" 등).
"""

import re

from django.db.models import Q

from blog.models import Post as Booking

NOT_A_HOME = re.compile(r'hotel|cruise|terminal|airport', re.IGNORECASE)
ABBREVIATIONS = [
    (re.compile(r'\bHts\b\.?', re.IGNORECASE), 'Heights'),
    (re.compile(r'\bNth\b\.?', re.IGNORECASE), 'North'),
    (re.compile(r'\bSth\b\.?', re.IGNORECASE), 'South'),
    (re.compile(r'\bMt\b\.?', re.IGNORECASE), 'Mount'),
]


def _key(name):
    return ' '.join((name or '').split()).lower()


def clean_suburb(value):
    """화면용 서버브 이름. 사는 곳이 아니거나 비었으면 ''."""
    text = ' '.join((value or '').split())
    if not text or NOT_A_HOME.search(text):
        return ''
    for pattern, full in ABBREVIATIONS:
        text = pattern.sub(full, text)
    return ' '.join(w if w.isupper() and len(w) > 1 else w.capitalize() for w in text.split())


def attach_suburbs(reviews):
    """각 리뷰에 .suburb 를 붙인다 (못 찾으면 '').

    같은 이름의 예약이 여러 개면 리뷰 날짜 이전 가장 최근 예약, 없으면 가장 최근
    예약의 서버브를 쓴다. 리뷰마다가 아니라 전체 한 번만 조회한다."""
    reviews = list(reviews)
    names = Q()
    for r in reviews:
        r.suburb = ''
        if _key(r.name):
            names |= Q(name__iexact=r.name.strip())
    if not names:
        return reviews

    by_name = {}
    rows = (Booking.objects.filter(names)
            .exclude(suburb__isnull=True).exclude(suburb='')
            .values_list('name', 'pickup_date', 'suburb')
            .order_by('-pickup_date', '-pk'))
    for name, pickup_date, suburb in rows:
        suburb = clean_suburb(suburb)
        if suburb:
            by_name.setdefault(_key(name), []).append((pickup_date, suburb))

    for r in reviews:
        bookings = by_name.get(_key(r.name), [])
        if bookings:
            before = [s for d, s in bookings if d and r.date and d <= r.date]
            r.suburb = before[0] if before else bookings[0][1]
    return reviews


def reviews_for_suburb(suburb_name, limit=5):
    """이 서버브에 사는 손님들이 남긴 공개 리뷰, 최신순 최대 limit 개.

    예약 서버브가 이 서버브인 손님 이름 → 그 이름의 리뷰 → attach_suburbs 로 다시
    확인해서 (리뷰 당시 다른 동네였던 사람 제외) 이 서버브인 것만 남긴다."""
    from easygo_review.models import Post as Review

    target = clean_suburb(suburb_name)
    if not target:
        return []
    variants = {target, suburb_name.strip()}
    for pattern, full in ABBREVIATIONS:          # 'Hornsby Heights' 는 'Hornsby Hts' 로도 적힌다
        short = {'Heights': 'Hts', 'North': 'Nth', 'South': 'Sth', 'Mount': 'Mt'}[full]
        variants |= {v.replace(full, short) for v in list(variants)}
    by_suburb = Q()
    for v in variants:
        by_suburb |= Q(suburb__iexact=v)
    names = {n.strip() for n in Booking.objects.filter(by_suburb).values_list('name', flat=True) if n and n.strip()}
    if not names:
        return []
    by_name = Q()
    for n in names:
        by_name |= Q(name__iexact=n)
    candidates = Review.objects.filter(by_name, is_published=True).order_by('-date', '-created')[:limit * 8]
    picked, seen = [], set()
    for r in attach_suburbs(candidates):         # 한 사람당 최신 리뷰 하나만
        if r.suburb == target and _key(r.name) not in seen:
            seen.add(_key(r.name))
            picked.append(r)
    return picked[:limit]


SERVICE_REVIEW_KINDS = ('region', 'cruise', 'group')


def reviews_for_service(kind, region_slug, limit=5, offset=0):
    """서비스 페이지용 후기 — 그 서비스를 실제로 이용한 손님의 공개 리뷰, 최신순, 한 사람당 하나.

    kind: 'region' 이 지역 예약 손님 / 'cruise' 크루즈 터미널 예약 / 'group' 7명 이상(맥시 택시).
    offset: 같은 지역의 airport-shuttle·airport-transfer 처럼 비슷한 두 페이지에 같은 후기가
    반복되지 않게 다른 묶음을 보여줄 때 쓴다. 결과는 dict 목록 (캐시에 넣기 좋게).
    """
    from easygo_review.models import Post as Review

    bookings = Booking.objects.filter(region__slug=region_slug, cancelled=False)
    if kind == 'cruise':
        bookings = bookings.filter(Q(cruise=True) | Q(suburb__icontains='cruise')
                                   | Q(start_point__icontains='cruise') | Q(end_point__icontains='cruise'))
    rows = bookings.values_list('name', 'no_of_passenger')
    if kind == 'group':
        rows = [(n, p) for n, p in rows if str(p or '').strip().isdigit() and int(str(p).strip()) >= 7]
    # 시드니는 예약자가 수천 명이라 이름마다 OR 조건을 거는 대신, 리뷰(수백 개)를 돌며 이름 집합과 맞춘다.
    names = {_key(n) for n, _ in rows if _key(n)}
    if not names:
        return []
    picked, seen = [], set()
    for r in Review.objects.filter(is_published=True).order_by('-date', '-created'):
        if _key(r.name) not in names or _key(r.name) in seen:
            continue
        seen.add(_key(r.name))
        picked.append(r)
        if len(picked) >= offset + limit:
            break
    return [{'name': r.name, 'date': r.date, 'rating': r.rating, 'url': r.get_absolute_url(),
             'text': r.get_markdown_content()} for r in picked[offset:offset + limit]]


def cached_service_reviews(kind, region_slug, offset=0):
    """SUBURB_LOCAL_REVIEWS 스위치가 켜져 있을 때만, 6시간 캐시."""
    from django.conf import settings
    from django.core.cache import cache

    if not getattr(settings, 'SUBURB_LOCAL_REVIEWS', False):
        return []
    key = f'service_reviews:v1:{kind}:{region_slug}:{offset}'
    result = cache.get(key)
    if result is None:
        result = reviews_for_service(kind, region_slug, offset=offset)
        cache.set(key, result, 60 * 60 * 6)
    return result
