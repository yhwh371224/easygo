from .models import Region

def region_config(request):
    """
    모든 템플릿에 region, current_region, active_regions 를 주입한다.

    - region       : 현재 페이지의 지역 (RegionMiddleware가 감지한 Region, 없으면 None)
    - current_region: RegionMiddleware가 URL에서 감지한 Region 객체 (없으면 None)
    - active_regions: 활성 Region 전체 목록
    """
    detected_region = getattr(request, 'region', None)

    active_regions = Region.objects.filter(is_active=True)

    # Many legacy URLs (e.g. "/") don't carry a region prefix. Templates still
    # expect `region` fields (phone/geo/name) to exist for SEO/schema and nav.
    # Fall back to Sydney when no region is detected.
    if isinstance(detected_region, Region):
        region = detected_region
        current_region = detected_region
    else:
        region = (
            active_regions.filter(slug='sydney').first()
            or active_regions.order_by('slug').first()
        )
        current_region = region

    return {
        'current_region': current_region,
        'active_regions': active_regions,
        'region': region,
        # Single business contact number across all pages/regions.
        'business_phone': '0406883355',
    }
