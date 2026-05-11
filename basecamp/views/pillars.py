import logging

from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.contrib.auth.decorators import login_required

from regions.models import Region, RegionSuburb
from regions.models import Terminal
from basecamp.area import get_suburbs
from basecamp.area_zones import area_zones
from basecamp.basecamp_utils import get_sorted_suburbs
from articles.models import Post

logger = logging.getLogger(__name__)


def _build_pillar_context(suburb_obj, zone_info):
    name = suburb_obj.name
    return {
        'suburb': name,
        'details': suburb_obj,
        'area_type': suburb_obj.zone,
        'main_suburbs': zone_info.get('main_suburbs', [name]),
        'title': zone_info.get('title', '').format(suburb=name),
        'meta_description': zone_info.get('meta_description', '').format(suburb=name),
        'h1': zone_info.get('h1', '').format(suburb=name),
        'h2': zone_info.get('h2', ''),
        'route_info': zone_info.get('route_info', '').format(suburb=name),
        'landmarks': zone_info.get('landmark', ''),
    }


def home(request):
    carousel_suburbs = get_suburbs()  # carousel - 그대로 유지
    region = get_object_or_404(Region, slug='sydney', is_active=True)
    home_suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')
    airport_terminals = Terminal.objects.filter(
        airport__in=region.airports.all()
    ).select_related("airport")
    rebook_error = request.session.pop('rebook_error', None)
    
    latest_post = Post.objects.filter(status='published').order_by('-created_at').first()

    return render(request, 'basecamp/home.html', {
        'carousel_suburbs': carousel_suburbs,
        'home_suburbs': home_suburbs,
        'airport_terminals': airport_terminals,
        'google_review_url': settings.GOOGLE_REVIEW_URL,
        'latest_post': latest_post,
        'rebook_error': rebook_error,

    })    



def maxi_taxi(request, suburb=None):
    if suburb and suburb != suburb.lower():
        return redirect('basecamp:maxi_taxi_suburb', suburb=suburb.lower(), permanent=True)
    
    if not suburb:
        return render(request, 'basecamp/pillars/maxi-taxi-pillar.html')
    
    suburb_obj = RegionSuburb.objects.filter(
        region__slug='sydney', slug=suburb, is_active=True,
    ).first()

    if not suburb_obj:
        return render(request, 'basecamp/pillars/maxi-taxi-pillar.html')

    zone_info = area_zones.get(suburb_obj.zone, {})
    context = _build_pillar_context(suburb_obj, zone_info)
    context['landmark'] = context['landmarks']
    context['page_bg'] = 'basecamp/photos/bg-pattern02.webp'

    return render(request, 'basecamp/pillars/airport-maxi-taxi.html', context)


def more_suburbs(request):
    suburbs = RegionSuburb.objects.filter(
        region__slug='sydney', is_active=True,
    ).order_by('name')
    return render(request, 'basecamp/layouts/more_suburbs.html', {'more_suburbs': suburbs})


def more_suburbs1(request):
    suburbs = RegionSuburb.objects.filter(
        region__slug='sydney', is_active=True,
    ).order_by('name')
    return render(request, 'basecamp/layouts/more_suburbs1.html', {'more_suburbs': suburbs})


def more_suburbs_maxi_taxi(request):
    suburbs = RegionSuburb.objects.filter(
        region__slug='sydney', is_active=True,
    ).order_by('name')
    return render(request, 'basecamp/layouts/more_suburbs_maxi_taxi.html', {'more_suburbs': suburbs})


def booking(request):
    return render(request, 'basecamp/booking/booking.html', {
        'home_suburbs': get_sorted_suburbs(),
    })


@login_required
def confirmation(request):
    return render(request, 'basecamp/booking/confirmation.html', {
        'home_suburbs': get_sorted_suburbs(),
        'ADMIN_URL': settings.SECRET_ADMIN_URL,
    })


def inquiry(request):
    return render(request, 'basecamp/booking/inquiry.html', {
        'home_suburbs': get_sorted_suburbs(),
    })


def inquiry1(request):
    return render(request, 'basecamp/booking/inquiry.html', {
        'pickup_date': None,
        'direction': None,
        'suburb': None,
        'no_of_passenger': None,
    })


def payonline(request):
    return render(request, 'basecamp/payments/payonline.html', {
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
    })
