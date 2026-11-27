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
