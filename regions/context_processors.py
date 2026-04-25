import types
from decimal import Decimal

from .models import Region

# Sydney 하드코딩 fallback — DB 연결 전/마이그레이션 전에도 템플릿이 깨지지 않도록.
# region.latitude/longitude는 easygo_base.html JSON-LD 기존 값과 완전히 일치.
_SYDNEY_FALLBACK = types.SimpleNamespace(
    slug='sydney',
    name='Sydney',
    state_code='NSW',
    timezone='Australia/Sydney',
    airport_code='SYD',
    airport_name='Sydney Airport (SYD)',
    airport_lat=Decimal('-33.9399'),
    airport_lng=Decimal('151.1753'),
    phone='+61406883355',
    phone_display='0406 883 355',
    address='Sydney, NSW',
    latitude=Decimal('-33.8261'),
    longitude=Decimal('151.2007'),
    meta_description=(
        'EasyGo Airport Shuttle provides private airport transfer across Sydney. '
        'Punctual, luggage-friendly service for individuals, families, and groups.'
    ),
    is_active=True,
)


def region_config(request):
    """
    모든 템플릿에 region, current_region, active_regions 를 주입한다.

    - region       : 현재 페이지의 지역 (URL 접두사 없으면 Sydney 기본값)
    - current_region: RegionMiddleware가 URL에서 감지한 Region 객체 (없으면 None)
    - active_regions: 활성 Region 전체 목록
    """
    current_region = getattr(request, 'region', None)

    active_regions = Region.objects.filter(is_active=True)

    if current_region is not None:
        region = current_region
    else:
        try:
            region = Region.objects.get(slug='sydney')
        except Region.DoesNotExist:
            region = _SYDNEY_FALLBACK

    return {
        'current_region': current_region,
        'active_regions': active_regions,
        'region': region,
    }
