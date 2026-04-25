from django.shortcuts import render, get_object_or_404
from .models import Region


def region_home(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'regions/home.html', {'region': region})


def region_booking(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'regions/booking.html', {'region': region})


def region_confirmation(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'regions/confirmation.html', {'region': region})


def airport_shuttle_landing(request, region_slug, suburb):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'regions/airport_shuttle.html', {
        'region': region,
        'suburb': suburb,
    })
