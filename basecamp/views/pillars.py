import logging
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from basecamp.area import get_suburbs
from basecamp.area_full import get_more_suburbs
from basecamp.area_home import get_home_suburbs
from basecamp.area_zones import area_zones
from basecamp.utils import get_sorted_suburbs

logger = logging.getLogger(__name__)


def home(request):
    suburbs = get_suburbs()
    sorted_home_suburbs = get_sorted_suburbs()

    logger.debug(f"home_suburbs count: {len(sorted_home_suburbs)}") 
    
    return render(request, 'basecamp/home.html', {
        'suburbs': suburbs,
        'home_suburbs': sorted_home_suburbs, 
        'google_review_url': settings.GOOGLE_REVIEW_URL,
    })

def airport_shuttle(request, suburb):
    more_suburbs = get_more_suburbs()

    if not suburb:
        return render(request, 'basecamp/pillars/sydney_airport_shuttle.html')
    
    suburb_formatted = suburb.replace('-', ' ').title() 

    if suburb_formatted in more_suburbs:
        details = more_suburbs[suburb_formatted]
        area_type = details['area_type']
        zone_info = area_zones.get(area_type, {})

        context = {
            'suburb': suburb_formatted,
            'details': details,
            'area_type': area_type,
            'main_suburbs': zone_info.get('main_suburbs', [suburb_formatted]),  
            'title': zone_info.get('title', "").format(suburb=suburb_formatted),
            'meta_description': zone_info.get('meta_description', "").format(suburb=suburb_formatted),
            'h1': zone_info.get('h1', "").format(suburb=suburb_formatted),
            'h2': zone_info.get('h2', ""),
            'route_info': zone_info.get('route_info', "").format(suburb=suburb_formatted),  
            'landmarks': zone_info.get('landmark', ""),
        }
        return render(request, 'basecamp/pillars/airport-shuttle-template.html', context)
    else:
        return render(request, 'basecamp/pillars/sydney_airport_shuttle.html')

def airport_transfer(request, suburb):
    more_suburbs = get_more_suburbs()

    if not suburb:
        return render(request, 'basecamp/pillars/sydney_airport_transfer.html')
    
    suburb_formatted = suburb.replace('-', ' ').title() 

    if suburb_formatted in more_suburbs:
        details = more_suburbs[suburb_formatted]
        area_type = details['area_type']
        zone_info = area_zones.get(area_type, {})

        context = {
            'suburb': suburb_formatted,
            'details': details,
            'area_type': area_type,
            'main_suburbs': zone_info.get('main_suburbs', [suburb_formatted]), 
            'title': zone_info.get('title', "").format(suburb=suburb_formatted),
            'meta_description': zone_info.get('meta_description', "").format(suburb=suburb_formatted),
            'h1': zone_info.get('h1', "").format(suburb=suburb_formatted),
            'h2': zone_info.get('h2', ""),
            'route_info': zone_info.get('route_info', "").format(suburb=suburb_formatted), 
            'landmarks': zone_info.get('landmark', ""),
        }
        return render(request, 'basecamp/pillars/airport-transfer-template.html', context)
    else:
        return render(request, 'basecamp/pillars/sydney_airport_transfer.html')

def maxi_taxi(request, suburb=None):
    more_suburbs = get_more_suburbs()

    if not suburb:
        return render(request, 'basecamp/pillars/maxi-taxi-pillar.html')

    suburb_formatted = suburb.replace('-', ' ').title()

    if suburb_formatted not in more_suburbs:
        return render(request, 'basecamp/pillars/maxi-taxi-pillar.html')

    details = more_suburbs[suburb_formatted]
    area_type = details.get('area_type')

    zone_info = area_zones.get(area_type, {})

    # 🔥 여기서 핵심: {suburb} 치환
    title = zone_info.get(
        'title',
        f"{suburb_formatted} Maxi Taxi Airport Transfer | EasyGo Airport Shuttle"
    ).format(suburb=suburb_formatted)

    meta_description = zone_info.get(
        'meta_description',
        f"Reliable maxi taxi service for {suburb_formatted} airport transfers"
    ).format(suburb=suburb_formatted)

    h1 = zone_info.get(
        'h1',
        f"{suburb_formatted} Maxi Taxi Airport Shuttle"
    ).format(suburb=suburb_formatted)

    h2 = zone_info.get('h2', "")

    context = {
        'suburb': suburb_formatted,
        'details': details,
        'title': title,
        'meta_description': meta_description,
        'h1': h1,
        'h2': h2,
        'route_info': zone_info.get('route_info', ""),
        'landmark': zone_info.get('landmark', ""),
        'page_bg': 'basecamp/photos/bg-pattern02.webp', 
    }

    return render(request, 'basecamp/pillars/airport-maxi-taxi.html', context)

def more_suburbs(request): 
    more_suburbs = get_more_suburbs()
    return render(request, 'basecamp/layouts/more_suburbs.html', {'more_suburbs': more_suburbs})

def more_suburbs1(request): 
    more_suburbs = get_more_suburbs()
    return render(request, 'basecamp/layouts/more_suburbs1.html', {'more_suburbs': more_suburbs})

def more_suburbs_maxi_taxi(request):
    more_suburbs = get_more_suburbs()
    return render(request, 'basecamp/layouts/more_suburbs_maxi_taxi.html', {'more_suburbs': more_suburbs})

# 중요한 pages.py 에 들어가야 할 단순렌더링
def booking(request):
    all_suburbs = get_home_suburbs()
    context = {
        'home_suburbs': all_suburbs,
    }
    return render(request, 'basecamp/booking/booking.html', context)

@login_required
def confirmation(request): 
    all_suburbs = get_home_suburbs()
    context = {
        'home_suburbs': all_suburbs,
    }
    return render(request, 'basecamp/booking/confirmation.html', context)

def inquiry(request):
    all_suburbs = get_sorted_suburbs()
    context = {
        'home_suburbs': all_suburbs,
    }
    return render(request, 'basecamp/booking/inquiry.html', context)

def inquiry1(request):
    context = {
        'pickup_date': None,
        'direction': None,
        'suburb': None,
        'no_of_passenger': None,
    }    
    return render(request, 'basecamp/booking/inquiry.html', context)

