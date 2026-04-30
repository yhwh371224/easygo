from .models import Region

def region_config(request):
    """
    모든 템플릿에 region, current_region, active_regions 를 주입한다.

    - region       : 현재 페이지의 지역 (RegionMiddleware가 감지한 Region, 없으면 None)
    - current_region: RegionMiddleware가 URL에서 감지한 Region 객체 (없으면 None)
    - active_regions: 활성 Region 전체 목록
    """
    current_region = getattr(request, 'region', None)

    active_regions = Region.objects.filter(is_active=True)

    region = current_region if isinstance(current_region, Region) else None

    return {
        'current_region': current_region,
        'active_regions': active_regions,
        'region': region,
    }
