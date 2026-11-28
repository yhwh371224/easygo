import logging

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template

from regions.models import Region, RegionSuburb, CruiseTerminal
from articles.models import Post as BlogPost

logger = logging.getLogger(__name__)


def _hero_image_urls(region):
    """URLs for the region hero photo: (base, 960px, 1600px).

    The width variants are pre-rendered files next to the original
    (e.g. brisbaneairport-960.webp). A region without them falls back to the
    original so a newly added hero image never 404s.
    """
    from django.contrib.staticfiles import finders

    name = region.hero_image_file
    stem, _, ext = name.rpartition('.')

    def variant(width):
        path = f'basecamp/photos/airports/{stem}-{width}.{ext}'
        return staticfiles_storage.url(path) if finders.find(path) else None

    base = staticfiles_storage.url(f'basecamp/photos/airports/{name}')
    return base, variant(960) or base, variant(1600) or base


def region_coming_soon(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    if not region.is_coming_soon:
        return redirect('regions:home', region_slug=region_slug, permanent=False)
    return render(request, 'regions/pages/coming_soon.html', {'region': region})


def region_home(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)

    if region.is_coming_soon:
        return render(request, 'regions/pages/coming_soon.html', {'region': region})

    form_suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')

    featured_suburbs = (
        region.suburbs
        .filter(is_active=True, is_featured=True)
        .only('name', 'slug', 'price', 'distance_km', 'region_id', 'meta_description', 'featured_order', 'carousel_image')
        .order_by('featured_order', 'name')[:5]
    )

    latest_post = (
        BlogPost.objects
        .filter(status='published')
        .filter(Q(regions=region) | Q(regions__isnull=True))
        .only('title', 'slug', 'created_at')
        .order_by('-created_at')
        .distinct()
        .first()
    )

    from regions.models import Terminal
    airport_terminals = Terminal.objects.filter(
        airport__regions=region
    ).select_related('airport').order_by('type', 'name')

    cruise_terminals = CruiseTerminal.objects.filter(region=region)

    hero_image_url, hero_image_url_sm, hero_image_url_lg = _hero_image_urls(region)

    return render(request, 'regions/pages/home.html', {
        'region': region,
        'form_suburbs': form_suburbs,
        'featured_suburbs': featured_suburbs,
        'airport_terminals': airport_terminals,
        'cruise_terminals': cruise_terminals,
        'latest_post': latest_post,
        'service_areas': region.service_areas or [],
        'hero_image_url': hero_image_url,
        'hero_image_url_sm': hero_image_url_sm,
        'hero_image_url_lg': hero_image_url_lg,
    })


def region_confirmation(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'regions/booking/confirmation.html', {'region': region})


def region_meeting_point(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    from regions.models import Terminal
    terminals = Terminal.objects.filter(airport__regions=region).select_related('airport')
    return render(request, 'regions/pages/meeting_point.html', {
        'region': region,
        'terminals': terminals,
    })


def region_arrival_guide(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    steps = [s.strip() for s in region.arrival_guide.split('\n') if s.strip()]
    return render(request, 'regions/pages/arrival_guide.html', {
        'region': region,
        'steps': steps,
    })


def _render_pillar(request, template_path):
    try:
        get_template(template_path)
    except TemplateDoesNotExist:
        raise Http404
    return render(request, template_path)


def _render_pillar_with_region(request, region_slug, template_path, reviews_kind=None,
                               reviews_offset=0, reviews_title=''):
    from easygo_review.review_region import cached_service_reviews
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    reviews = cached_service_reviews(reviews_kind, region.slug, reviews_offset) if reviews_kind else []
    return render(request, template_path, {
        'region': region, 'reviews': reviews, 'reviews_title': reviews_title,
    })


# 서비스 페이지 후기 (SUBURB_LOCAL_REVIEWS 스위치): 그 서비스를 실제로 이용한 손님 후기.
# shuttle·transfer 페이지는 내용이 비슷하니 서로 다른 후기 묶음을 보여준다 (offset 0 / 5).
def region_airport_shuttle(request, region_slug):
    return _render_pillar_with_region(request, region_slug, 'regions/pillars/airport_shuttle.html',
                                      'region', 0, 'What our customers say')


def region_airport_transfer(request, region_slug):
    return _render_pillar_with_region(request, region_slug, 'regions/pillars/airport_transfer.html',
                                      'region', 5, 'Recent customer reviews')


def region_cruise_transfer(request, region_slug):
    return _render_pillar_with_region(request, region_slug, 'regions/pillars/cruise_transfer.html',
                                      'cruise', 0, 'What our cruise customers say')


def region_maxi_taxi(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    pinned_suburbs = (
        RegionSuburb.objects
        .filter(region=region, is_active=True, is_pinned=True)
        .order_by('sort_order', 'name')
    )
    from easygo_review.review_region import cached_service_reviews
    return render(request, 'regions/pillars/maxi_taxi.html', {
        'region': region,
        'pinned_suburbs': pinned_suburbs,
        'reviews': cached_service_reviews('group', region.slug),
        'reviews_title': 'What groups of 7–13 say',
    })


def region_airport_shuttle_list(request, region_slug):
    return redirect('regions:home', region_slug=region_slug, permanent=False)


def airport_shuttle_suburb(request, region_slug, suburb_slug, service_type='shuttle'):
    region = get_object_or_404(
        Region.objects.select_related('primary_airport'),
        slug=region_slug, is_active=True,
    )
    suburb = get_object_or_404(
        RegionSuburb, region=region, slug=suburb_slug, is_active=True,
    )
    # shuttle/transfer 합치기 (regions/suburb_merge.py, 스위치로 켬): 남긴 페이지가 아니면 301.
    from regions.suburb_merge import kept_service, local_reviews_on, suburb_url
    kept = kept_service(region.slug, suburb.slug)
    if kept and kept != service_type:
        return redirect(suburb_url(region.slug, suburb.slug), permanent=True)
    zone_suburbs = list(
        RegionSuburb.objects
        .filter(region=region, zone=suburb.zone, is_active=True)
        .exclude(slug=suburb_slug)
        .order_by('name')
    )
    # 같은 구역 60여 개를 다 붙이면 본문보다 링크가 길어진다 — 공항 거리가 비슷한
    # (= 대체로 가까운) 12곳만 보여준다.
    if suburb.distance_km is not None:
        zone_suburbs.sort(key=lambda s: (
            s.distance_km is None,
            abs((s.distance_km or 0) - suburb.distance_km),
            s.name,
        ))
    zone_suburbs = sorted(zone_suburbs[:12], key=lambda s: s.name)

    for s in zone_suburbs:
        s.page_url = suburb_url(region.slug, s.slug, service_type)

    local_reviews = []
    if local_reviews_on(region.slug, suburb.slug, service_type):
        from django.core.cache import cache
        from easygo_review.review_region import reviews_for_suburb
        key = f'suburb_reviews:v2:{region.slug}:{suburb.slug}'
        local_reviews = cache.get(key)
        if local_reviews is None:
            local_reviews = [
                {'name': r.name, 'date': r.date, 'rating': r.rating, 'url': r.get_absolute_url(),
                 'text': r.get_markdown_content()}
                for r in reviews_for_suburb(suburb.name)
            ]
            cache.set(key, local_reviews, 60 * 60 * 6)

    service_label = 'Airport Transfer' if service_type == 'transfer' else 'Airport Shuttle'
    service_path = 'airport-transfer' if service_type == 'transfer' else 'airport-shuttle'
    return render(request, 'regions/pages/airport_shuttle_suburb.html', {
        'region': region,
        'suburb': suburb,
        'zone_suburbs': zone_suburbs,
        # 합쳐진 서버브 — 남은 한 페이지가 shuttle·transfer 검색어를 다 받는다.
        'merged': bool(kept),
        'local_reviews': local_reviews,
        'current_region': region,
        'service_type': service_type,
        'service_label': service_label,
        'service_path': service_path,
        # 인원별 가격표·할증 안내는 가격 규칙 기준이라 실제 (수동) 견적과 안 맞는다 —
        # 실제 가격 기준이 정해질 때까지 숨긴다.
        'price_table': [],
        'surcharges': [],
    })


def region_inquiry_done(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'basecamp/inquiry_done.html', {
        'region': region,
        'current_region': region,
    })


def region_more_suburbs(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    suburbs = RegionSuburb.objects.filter(
        region=region, is_active=True
    ).order_by('name')
    return render(request, 'regions/pages/regions_more_suburbs.html', {
        'region': region,
        'current_region': region,
        'suburbs': suburbs,
    })


def _build_city_context(request, slug):
    region = get_object_or_404(Region, slug=slug, is_active=True)
    form_suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')
    featured_suburbs = (
        region.suburbs
        .filter(is_active=True, is_featured=True)
        .only('name', 'slug', 'price', 'distance_km', 'region_id', 'meta_description', 'featured_order', 'carousel_image')
        .order_by('featured_order', 'name')[:5]
    )
    latest_post = (
        BlogPost.objects
        .filter(status='published')
        .filter(Q(regions=region) | Q(regions__isnull=True))
        .only('title', 'slug', 'created_at')
        .order_by('-created_at')
        .distinct()
        .first()
    )
    from regions.models import Terminal
    airport_terminals = Terminal.objects.filter(
        airport__regions=region
    ).select_related('airport').order_by('type', 'name')
    cruise_terminals = CruiseTerminal.objects.filter(region=region)
    hero_image_url, hero_image_url_sm, hero_image_url_lg = _hero_image_urls(region)
    return {
        'region': region,
        'form_suburbs': form_suburbs,
        'featured_suburbs': featured_suburbs,
        'airport_terminals': airport_terminals,
        'cruise_terminals': cruise_terminals,
        'latest_post': latest_post,
        'service_areas': region.service_areas or [],
        'hero_image_url': hero_image_url,
        'hero_image_url_sm': hero_image_url_sm,
        'hero_image_url_lg': hero_image_url_lg,
    }


def brisbane_home(request):
    ctx = _build_city_context(request, 'brisbane')
    return render(request, 'regions/pages/brisbane_home.html', ctx)


def melbourne_home(request):
    ctx = _build_city_context(request, 'melbourne')
    return render(request, 'regions/pages/melbourne_home.html', ctx)


def gold_coast_home(request):
    ctx = _build_city_context(request, 'gold-coast')
    return render(request, 'regions/pages/gold_coast_home.html', ctx)