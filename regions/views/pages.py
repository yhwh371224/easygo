import logging

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404

from regions.models import Region, RegionSuburb
from articles.models import Post as BlogPost

logger = logging.getLogger(__name__)


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
        .only('name', 'slug', 'price', 'meta_description', 'featured_order')
        .order_by('featured_order', 'name')[:7]
    )

    latest_post = (
        BlogPost.objects
        .filter(status='published', region=region)
        .only('title', 'slug', 'created_at')
        .order_by('-created_at')
        .first()
    )

    from regions.models import Terminal
    airport_terminals = Terminal.objects.filter(
        airport__regions=region
    ).select_related('airport').order_by('type', 'name')

    return render(request, 'regions/pages/home.html', {
        'region': region,
        'form_suburbs': form_suburbs,
        'featured_suburbs': featured_suburbs,
        'airport_terminals': airport_terminals,
        'google_review_url': settings.GOOGLE_REVIEW_URL,
        'latest_post': latest_post,
    })


def region_confirmation(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'regions/booking/confirmation.html', {'region': region})


def region_meeting_point(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    terminals = region.terminal_info or []
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


def region_airport_shuttle_list(request, region_slug):
    return redirect('regions:home', region_slug=region_slug, permanent=True)


def airport_shuttle_suburb(request, region_slug, suburb_slug):
    region = get_object_or_404(
        Region.objects.select_related('primary_airport'),
        slug=region_slug, is_active=True,
    )
    suburb = get_object_or_404(
        RegionSuburb, region=region, slug=suburb_slug, is_active=True,
    )
    zone_suburbs = (
        RegionSuburb.objects
        .filter(region=region, zone=suburb.zone, is_active=True)
        .exclude(slug=suburb_slug)
        .order_by('name')
    )
    return render(request, 'regions/pages/airport_shuttle_suburb.html', {
        'region': region,
        'suburb': suburb,
        'zone_suburbs': zone_suburbs,
    })
