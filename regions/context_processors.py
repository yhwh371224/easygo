from .models import Region


def region_config(request):
    """
    활성 리전 목록과 현재 request.region을 템플릿에 전달한다.
    RegionMiddleware가 먼저 실행되어야 request.region이 세팅된다.
    """
    current_region = getattr(request, 'region', None)
    active_regions = Region.objects.filter(is_active=True)

    return {
        'current_region': current_region,
        'active_regions': active_regions,
    }
