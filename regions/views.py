import asyncio
import logging

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from .models import Region, RegionSuburb
from .area import get_suburbs
from articles.models import Post as BlogPost
from blog.models import Post as Booking, Inquiry, Driver
from blog.blog_utils import get_default_driver_for_region
from basecamp.basecamp_utils import (
    is_ajax, parse_baggage, parse_booking_dates,
    booking_success_response, require_turnstile, is_duplicate_submission,
    get_client_ip,
)
from utils.telegram import send_telegram_notification

logger = logging.getLogger(__name__)
from .models import RequestLog


def region_price_detail(request, region_slug):
    """
    Region-aware wrapper for legacy /price_detail/ (basecamp).
    RegionMiddleware injects request.region based on the URL prefix.
    """
    from basecamp.views.misc_inquirys import price_detail
    return price_detail(request)


def region_inquiry_details1(request, region_slug):
    """
    Region-aware wrapper for legacy /inquiry_details1/ (basecamp).
    RegionMiddleware injects request.region based on the URL prefix.
    """
    from basecamp.views.inquirys import inquiry_details1
    return inquiry_details1(request)


def region_p2p_detail(request, region_slug):
    """
    Region-aware wrapper for legacy /p2p_detail/ (basecamp).
    RegionMiddleware injects request.region based on the URL prefix.
    """
    from basecamp.views.inquirys import p2p_detail
    return p2p_detail(request)


def region_p2p_booking(request, region_slug):
    """
    Region-aware wrapper for /p2p_booking/ (basecamp).
    """
    from basecamp.views.pages import p2p_booking
    return p2p_booking(request)


def region_p2p_multi(request, region_slug):
    """
    Region-aware wrapper for /p2p_multi/ (basecamp).
    """
    from basecamp.views.pages import p2p_multi
    return p2p_multi(request)


def region_p2p_booking_detail(request, region_slug):
    """
    Region-aware wrapper for /p2p_booking_detail/ (basecamp booking).
    """
    from basecamp.views.bookings import p2p_booking_detail
    return p2p_booking_detail(request)


# ── Coming Soon ───────────────────────────────────────────────────────────────

def region_coming_soon(request, region_slug):
    """
    Coming soon landing for regions not yet launched.
    """
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    if not region.is_coming_soon:
        return redirect('regions:home', region_slug=region_slug, permanent=False)

    return render(request, 'regions/coming_soon.html', {'region': region})


# ── Home ──────────────────────────────────────────────────────────────────────

def region_home(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)

    if region.is_coming_soon:
        return render(request, 'regions/coming_soon.html', {'region': region})

     # Booking form용 (전체 활성 suburb)
    form_suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')

    # Carousel용 (featured 6개)
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

    from .models import Terminal
    airport_terminals = Terminal.objects.filter(
        airport__regions=region
    ).select_related('airport').order_by('type', 'name')

    return render(request, 'regions/home.html', {
        'region': region,
        'form_suburbs': form_suburbs,
        'featured_suburbs': featured_suburbs,
        'airport_terminals': airport_terminals,
        'google_review_url': settings.GOOGLE_REVIEW_URL,
        'latest_post': latest_post,
    })


# ── Inquiry ───────────────────────────────────────────────────────────────────

def region_inquiry(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')
    return render(request, 'regions/inquiry.html', {
        'region': region,
        'suburbs': suburbs,
    })


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_turnstile
def region_inquiry_details(request, region_slug):
    if request.method == 'POST':
        region = get_object_or_404(Region, slug=region_slug, is_active=True)
        logger.info(
            f"[INQUIRY] IP={get_client_ip(request)} "
            f"path={request.path} "
            f"email={request.POST.get('email')}"
        )
        RequestLog.objects.create(
            region=region,
            path=request.path,
            ip=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        name = request.POST.get('name', '')
        contact = request.POST.get('contact', '')
        email = request.POST.get('email', '')
        pickup_date_str = request.POST.get('pickup_date', '')
        return_pickup_date_str = request.POST.get('return_pickup_date', '')
        flight_number = request.POST.get('flight_number', '')
        flight_time = request.POST.get('flight_time', '')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb', '')
        start_point = request.POST.get('start_point', '')
        end_point = request.POST.get('end_point', '')
        street = request.POST.get('street', '')
        no_of_passenger = request.POST.get('no_of_passenger', '')
        return_direction = request.POST.get('return_direction', '')
        return_flight_number = request.POST.get('return_flight_number', '')
        return_flight_time = request.POST.get('return_flight_time', '')
        return_pickup_time = request.POST.get('return_pickup_time')
        return_start_point = request.POST.get('return_start_point', '')
        return_end_point = request.POST.get('return_end_point', '')
        message = request.POST.get('message', '')

        if is_duplicate_submission(Inquiry, email):
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})

        try:
            pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date_str, return_pickup_date_str)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        baggage_str = parse_baggage(request)

        p = Inquiry(
            name=name, contact=contact, email=email,
            pickup_date=pickup_date_obj,
            flight_number=flight_number, flight_time=flight_time,
            pickup_time=pickup_time, direction=direction, suburb=suburb,
            street=street, start_point=start_point, end_point=end_point,
            no_of_passenger=no_of_passenger, no_of_baggage=baggage_str,
            return_direction=return_direction,
            return_pickup_date=return_pickup_date_obj,
            return_flight_number=return_flight_number, return_flight_time=return_flight_time,
            return_pickup_time=return_pickup_time, return_start_point=return_start_point,
            return_end_point=return_end_point, message=message,
        )
        p.region = region
        p.save()

        asyncio.run(send_telegram_notification("✈️ New inquiry has been received."))
        return booking_success_response(request)

    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')
    return render(request, 'regions/inquiry.html', {'region': region, 'suburbs': suburbs})


# ── Booking ───────────────────────────────────────────────────────────────────

def region_booking(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')
    return render(request, 'regions/booking.html', {
        'region': region,
        'suburbs': suburbs,
    })


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_turnstile
def region_booking_detail(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)

    if request.method == 'POST':        
        logger.info(
            f"[BOOKING] IP={get_client_ip(request)} "
            f"path={request.path} "
            f"email={request.POST.get('email')}"
        )
        RequestLog.objects.create(
            region=region,
            path=request.path,
            ip=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        pickup_date_str = request.POST.get('pickup_date', '')
        return_pickup_date_str = request.POST.get('return_pickup_date', '')
        flight_number = request.POST.get('flight_number', '')
        flight_time = request.POST.get('flight_time', '')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb', '')
        street = request.POST.get('street')
        start_point = request.POST.get('start_point', '')
        end_point = request.POST.get('end_point', '')
        no_of_passenger = request.POST.get('no_of_passenger')
        return_direction = request.POST.get('return_direction', '')
        return_flight_number = request.POST.get('return_flight_number', '')
        return_flight_time = request.POST.get('return_flight_time', '')
        return_pickup_time = request.POST.get('return_pickup_time', '')
        return_start_point = request.POST.get('return_start_point', '')
        return_end_point = request.POST.get('return_end_point', '')
        message = request.POST.get('message')

        if is_duplicate_submission(Booking, email):
            return JsonResponse({'success': False, 'message': 'Duplicate form recently submitted. Please wait before trying again.'})

        try:
            pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date_str, return_pickup_date_str)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        baggage_str = parse_baggage(request)
        driver = get_default_driver_for_region(region)

        asyncio.run(send_telegram_notification("✈️ New airport booking has been received."))

        p = Booking(
            name=name, contact=contact, email=email,
            pickup_date=pickup_date_obj,
            flight_number=flight_number, flight_time=flight_time,
            pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
            start_point=start_point, end_point=end_point,
            no_of_passenger=no_of_passenger, no_of_baggage=baggage_str, message=message,
            return_direction=return_direction,
            return_pickup_date=return_pickup_date_obj,
            return_flight_number=return_flight_number, return_flight_time=return_flight_time,
            return_pickup_time=return_pickup_time, return_start_point=return_start_point,
            return_end_point=return_end_point,
            driver=driver, price='TBA', pending=True, reminder=False,
        )
        p.region = region
        p.save()

        return booking_success_response(request)

    suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')
    return render(request, 'regions/booking.html', {'region': region, 'suburbs': suburbs})


# ── Confirmation ──────────────────────────────────────────────────────────────

def region_confirmation(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    return render(request, 'regions/confirmation.html', {'region': region})


# ── Meeting Point ─────────────────────────────────────────────────────────────

def region_meeting_point(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    terminals = region.terminal_info or []
    return render(request, 'regions/meeting_point.html', {
        'region': region,
        'terminals': terminals,
    })


# ── Arrival Guide ─────────────────────────────────────────────────────────────

def region_arrival_guide(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    steps = [s.strip() for s in region.arrival_guide.split('\n') if s.strip()]
    return render(request, 'regions/arrival_guide.html', {
        'region': region,
        'steps': steps,
    })


# ── Airport Shuttle ───────────────────────────────────────────────────────────

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
    return render(request, 'regions/airport_shuttle_suburb.html', {
        'region': region,
        'suburb': suburb,
        'zone_suburbs': zone_suburbs,
    })
