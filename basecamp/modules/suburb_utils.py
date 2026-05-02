from regions.models import RegionSuburb


def get_sorted_suburbs(region_slug='sydney'):
    qs = RegionSuburb.objects.filter(
        region__slug=region_slug,
        is_active=True,
    ).order_by('-is_pinned', 'sort_order', 'name')
    return [s.name for s in qs]
