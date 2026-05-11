import logging

from django.conf import settings
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template

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

    rebook_error = request.session.pop('rebook_error', None)

    return render(request, 'regions/pages/home.html', {
        'region': region,
        'form_suburbs': form_suburbs,
        'featured_suburbs': featured_suburbs,
        'airport_terminals': airport_terminals,
        'google_review_url': settings.GOOGLE_REVIEW_URL,
        'latest_post': latest_post,
        'rebook_error': rebook_error,
        'service_areas': region.service_areas or [],
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


def _render_pillar(request, template_path):
    try:
        get_template(template_path)
    except TemplateDoesNotExist:
        raise Http404
    return render(request, template_path)


def _render_pillar_with_region(request, region_slug, template_path):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, template_path, {'region': region})


def region_airport_shuttle(request, region_slug):
    return _render_pillar_with_region(request, region_slug, 'regions/pillars/airport_shuttle.html')


def region_airport_transfer(request, region_slug):
    return _render_pillar_with_region(request, region_slug, 'regions/pillars/airport_transfer.html')


def region_cruise_transfer(request, region_slug):
    return _render_pillar_with_region(request, region_slug, 'regions/pillars/cruise_transfer.html')


def region_maxi_taxi(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    pinned_suburbs = (
        RegionSuburb.objects
        .filter(region=region, is_active=True, is_pinned=True)
        .order_by('sort_order', 'name')
    )
    return render(request, 'regions/pillars/maxi_taxi.html', {
        'region': region,
        'pinned_suburbs': pinned_suburbs,
    })


def region_airport_shuttle_list(request, region_slug):
    return redirect('regions:home', region_slug=region_slug, permanent=False)


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
        'current_region': region,
    })


def region_inquiry_done(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'basecamp/inquiry_done.html', {
        'region': region,
        'current_region': region,
        'google_review_url': settings.GOOGLE_REVIEW_URL,
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