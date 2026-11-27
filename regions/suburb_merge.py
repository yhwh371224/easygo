"""서버브 shuttle / transfer 페이지 합치기 (SEO 실험, 스위치로 켜고 끈다).

같은 서버브에 /airport-shuttle/<slug>/ 와 /airport-transfer/<slug>/ 두 페이지가 거의 같은
내용으로 같은 검색어를 두고 경쟁한다 (2026-11-24 확인: penrith, hornsby, chatswood,
bondi junction 이 두 URL 다 7–10위). 합치면 하나만 남기고 다른 쪽은 남긴 쪽으로 301.

스위치 (vultr .env, 기본 꺼짐 — 2026-11-28 준비만 해 둠):
    SUBURB_MERGE_MEL_GC=True          Melbourne / Gold Coast: transfer → shuttle (shuttle 이 압도적)
    SUBURB_MERGE_SYDNEY_PILOT=True    Sydney 시범 21곳만 (SYDNEY_PILOT_KEEP). 비교 20곳은 그대로.

12월 코어 업데이트 완료 + 1주 뒤에 켠다. 켜는 날을 SEO 변경 기록에 남긴다.
시범 명단: ~/Desktop/SEO/sydney_merge_pilot_2026-11-24.csv (8/13–11/12 GSC, 두 페이지 다
노출 100+ 인 41곳을 클릭 순으로 번갈아 나눔). 남길 쪽 = 클릭이 더 많은 페이지.
"""

from django.conf import settings

SHUTTLE = 'shuttle'
TRANSFER = 'transfer'
SERVICE_PATH = {SHUTTLE: 'airport-shuttle', TRANSFER: 'airport-transfer'}

MEL_GC_REGIONS = ('melbourne', 'gold-coast')

# 시범 그룹 — 서버브 slug → 남길 페이지.
SYDNEY_PILOT_KEEP = {
    'penrith': 'transfer',           # 84 clicks (8/13–11/12)
    'castle-hill': 'transfer',       # 56 clicks (8/13–11/12)
    'chatswood': 'transfer',         # 41 clicks (8/13–11/12)
    'box-hill': 'shuttle',          # 25 clicks (8/13–11/12)
    'marsden-park': 'transfer',      # 23 clicks (8/13–11/12)
    'rouse-hill': 'transfer',        # 22 clicks (8/13–11/12)
    'kellyville': 'transfer',        # 19 clicks (8/13–11/12)
    'st-marys': 'shuttle',          # 16 clicks (8/13–11/12)
    'bondi-junction': 'shuttle',    # 15 clicks (8/13–11/12)
    'thornleigh': 'shuttle',        # 14 clicks (8/13–11/12)
    'st-clair': 'transfer',          # 12 clicks (8/13–11/12)
    'mosman': 'shuttle',            # 12 clicks (8/13–11/12)
    'greystanes': 'shuttle',        # 10 clicks (8/13–11/12)
    'coogee': 'shuttle',            # 9 clicks (8/13–11/12)
    'cremorne': 'shuttle',          # 8 clicks (8/13–11/12)
    'pyrmont': 'shuttle',           # 6 clicks (8/13–11/12)
    'beecroft': 'shuttle',          # 5 clicks (8/13–11/12)
    'artarmon': 'shuttle',          # 5 clicks (8/13–11/12)
    'five-dock': 'transfer',         # 5 clicks (8/13–11/12)
    'eastwood': 'transfer',          # 4 clicks (8/13–11/12)
    'belmore': 'shuttle',           # 0 clicks (8/13–11/12)
}

# 비교(대조) 그룹 — 합치지 않고 그대로 둔다. 시범 그룹과 순위·클릭을 비교할 때 쓴다.
SYDNEY_CONTROL = (
    'hornsby',
    'parramatta',
    'glenwood',
    'baulkham-hills',
    'epping',
    'mt-druitt',
    'macquarie-park',
    'pennant-hills',
    'olympic-park',
    'bankstown',
    'schofields',
    'bondi-beach',
    'rooty-hill',
    'richmond',
    'ryde',
    'north-sydney',
    'marrickville',
    'revesby',
    'normanhurst',
    'rhodes',
)

def kept_service(region_slug, suburb_slug):
    """합쳐진 서버브면 남길 페이지 ('shuttle'/'transfer'), 아니면 None (두 페이지 다 유지)."""
    if getattr(settings, 'SUBURB_MERGE_MEL_GC', False) and region_slug in MEL_GC_REGIONS:
        return SHUTTLE
    if getattr(settings, 'SUBURB_MERGE_SYDNEY_PILOT', False) and region_slug == 'sydney':
        return SYDNEY_PILOT_KEEP.get(suburb_slug)
    return None


def suburb_url(region_slug, suburb_slug, service=SHUTTLE):
    """서버브 페이지 주소. 합쳐진 서버브는 남은 페이지 주소를 준다 (301 을 거치지 않게)."""
    service = kept_service(region_slug, suburb_slug) or service
    return f'/{region_slug}/{SERVICE_PATH[service]}/{suburb_slug}/'


def sitemap_services(region_slug, suburb_slug):
    """사이트맵에 넣을 서비스들 — 합쳐진 서버브는 남은 하나만."""
    kept = kept_service(region_slug, suburb_slug)
    return (kept,) if kept else (SHUTTLE, TRANSFER)


def local_reviews_on(region_slug, suburb_slug, service):
    """동네 후기를 이 페이지에 보여줄지. 같은 후기가 shuttle·transfer 두 페이지에 똑같이
    나오지 않게 한 쪽에만 — 합쳐진 서버브는 남은 페이지, 아니면 shuttle 페이지."""
    if not getattr(settings, 'SUBURB_LOCAL_REVIEWS', False):
        return False
    return service == (kept_service(region_slug, suburb_slug) or SHUTTLE)
