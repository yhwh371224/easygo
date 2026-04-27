from regions.models import RegionSuburb


def get_sorted_suburbs():
    qs = RegionSuburb.objects.filter(
        region__slug='sydney',
        is_active=True,
    ).order_by('-is_pinned', 'sort_order', 'name')
    return [s.name for s in qs]
