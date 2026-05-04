from django.shortcuts import get_object_or_404
from regions.models import Region


def make_region_view(basecamp_view_func):
    def wrapper(request, region_slug, *args, **kwargs):
        region = get_object_or_404(Region, slug=region_slug, is_active=True)
        request.region = region
        return basecamp_view_func(request, *args, **kwargs)
    return wrapper


