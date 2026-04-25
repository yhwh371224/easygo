from django.shortcuts import render, get_object_or_404
from .models import Region, RegionSuburb


def region_home(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    suburbs = region.suburbs.filter(is_active=True).order_by('zone', 'name')
    return render(request, 'regions/home.html', {
        'region': region,
        'suburbs': suburbs,
    })


def region_booking(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'regions/booking.html', {'region': region})


def region_confirmation(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'regions/confirmation.html', {'region': region})


def airport_shuttle_suburb(request, region_slug, suburb_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    suburb = get_object_or_404(RegionSuburb, region=region, slug=suburb_slug, is_active=True)
    return render(request, 'regions/airport_shuttle_suburb.html', {
        'region': region,
        'suburb': suburb,
    })
