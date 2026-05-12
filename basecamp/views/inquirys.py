import asyncio
import logging

from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from requests import request
from blog.models import Inquiry
from regions.models import Region
from regions.models import Terminal
from basecamp.basecamp_utils import (
    is_ajax, parse_baggage, parse_date, handle_email_sending,
    verify_turnstile,
    render_inquiry_done, booking_success_response, require_turnstile,
    is_duplicate_submission, parse_booking_dates, get_customer_status,
    get_client_ip,
)
from django_ratelimit.decorators import ratelimit
from regions.models.airport import CruiseTerminal
from utils.telegram import send_telegram_notification, get_ip_info
from regions.models import RequestLog

logger = logging.getLogger(__name__)


def _get_request_region(request):
    """URL 접두사에서 감지된 Region을 반환. 없으면 None."""
    region = getattr(request, 'region', None)
    if isinstance(region, Region):
        return region
    return None


def _terminals_for_region(region: Region):
    if not region:
        return Terminal.objects.none()
    return Terminal.objects.filter(airport__regions=region).select_related("airport")


def _resolve_terminal(region: Region, raw_value: str):
    """
    Resolve a Terminal object from a form value.
    - Preferred: terminal id (stringified int)
    """
    if not region or not raw_value:
        return None
    qs = _terminals_for_region(region)
    value = str(raw_value).strip()

    if value.isdigit():
        return qs.filter(pk=int(value)).first()

    return None


def _resolve_cruise_terminal(region: Region, raw_value: str):
    if not region or not raw_value:
        return None
    value = str(raw_value).strip()
    if value.isdigit():
        return CruiseTerminal.objects.filter(pk=int(value), region=region).first()
    return None


# Inquiry for airport (BOOk NOW/New Booking button)
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_turnstile
def inquiry_details(request):
    if request.method == "POST":
        post_region = _get_request_region(request)
        if not post_region:
            region_slug = request.POST.get('region')
            if region_slug:
                post_region = Region.objects.filter(slug=region_slug, is_active=True).first()

        # Sydney fallback
        if not post_region:
            post_region = Region.objects.filter(slug='sydney', is_active=True).first()
        
        logger.info(
            f"[INQUIRY] IP={get_client_ip(request)} "
            f"path={request.path} "
            f"email={request.POST.get('email')}"
        )
        
        name = request.POST.get('name', '')
        contact = request.POST.get('contact', '')
        email = request.POST.get('email', '')  

        # ✅ Collect date strings
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

        # ✅ 중복 제출 방지
        if is_duplicate_submission(Inquiry, email):
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})

        try:
            pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date_str, return_pickup_date_str)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})            

        # 🧳 개별 수하물 항목 수집
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
            return_end_point=return_end_point, message=message, region=post_region,
        )

        p.save()

        ip = get_client_ip(request)
        ip_info = get_ip_info(ip)
        try:
            asyncio.run(send_telegram_notification(
                f"✈️ New inquiry:\n"
                f"Region: {post_region.name if post_region else 'Unknown'}\n"
                f"IP: `{ip}`\n"
                f"Location: {ip_info}"
            ))
        except Exception as e:
            logger.error(f"[TELEGRAM] Failed to send: {e}")

        return booking_success_response(request)

    else:
        active_regions = Region.objects.filter(is_active=True)
        region = _get_request_region(request)
        if not region:
            region = Region.objects.filter(slug='sydney', is_active=True).first()
        return render(request, 'basecamp/booking/inquiry.html', {
            "region": region,
            "active_regions": active_regions,
        })


# inquiry (simple one) for airport from home page
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_turnstile
def inquiry_details1(request):
    if request.method == "POST":
        post_region = _get_request_region(request)
        if not post_region:
            region_slug = request.POST.get('region')
            if region_slug:
                post_region = Region.objects.filter(slug=region_slug, is_active=True).first()      
        logger.info(
            f"[INQUIRY] IP={get_client_ip(request)} "
            f"path={request.path} "
            f"email={request.POST.get('email')}"
        )
        
        pickup_date_str = request.POST.get('pickup_date', '')
        name = request.POST.get('name', '')
        contact = request.POST.get('contact', '')
        email = request.POST.get('email', '')
        flight_number = request.POST.get('flight_number', '')
        flight_time = request.POST.get('flight_time', '')
        pickup_time = request.POST.get('pickup_time', '')
        start_point = request.POST.get('start_point', '')
        end_point = request.POST.get('end_point', '')        
        street = request.POST.get('street', '')  
        no_of_passenger = request.POST.get('no_of_passenger', '')
        message = request.POST.get('message', '')
        
        # Prefer explicitly carried values (e.g., terminal IDs) over session fallback.
        original_start_point = (
            request.POST.get('original_start_point')
            or request.session.get('original_start_point')
            or start_point
        )
        original_end_point = (
            request.POST.get('original_end_point')
            or request.session.get('original_end_point')
            or end_point
        )
        
        direction = ""
        suburb = ""

        region = post_region
        if not region:
            # Region selection is mandatory for terminal-based inquiry routing.
            if is_ajax(request):
                return JsonResponse({'success': False, 'message': 'Region is required. Please select your city and try again.'}, status=400)
            return render(request, '400.html', status=400)

        try:
            pickup_date_obj = parse_date(pickup_date_str, field_name="Pickup Date", required=True)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        if is_duplicate_submission(Inquiry, email, region_slug=post_region.slug if post_region else None):
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})

        start_terminal = _resolve_terminal(region, original_start_point)
        end_terminal = _resolve_terminal(region, original_end_point)

        direction = ""
        suburb = ""

        # ❗ 핵심 추가: region 없으면 무조건 skip
        if not region:
            start_terminal = None
            end_terminal = None

        # ✅ 1. pickup 우선
        if start_terminal:
            if start_terminal.type == Terminal.TerminalType.INTL:
                direction = 'Pickup from Intl Airport'
                suburb = original_end_point
                start_point = ''
                end_point = ''
            elif start_terminal.type == Terminal.TerminalType.DOMESTIC:
                direction = 'Pickup from Domestic Airport'
                suburb = original_end_point
                start_point = ''
                end_point = ''

        # ✅ 2. dropoff (pickup 없을 때만)
        elif end_terminal:
            if end_terminal.type == Terminal.TerminalType.INTL:
                direction = 'Drop off to Intl Airport'
                suburb = original_start_point
                start_point = ''
                end_point = ''
            elif end_terminal.type == Terminal.TerminalType.DOMESTIC:
                direction = 'Drop off to Domestic Airport'
                suburb = original_start_point
                start_point = ''
                end_point = ''

        # Fallback: if normalized "Airport" got posted without a terminal id.
        elif str(original_start_point).strip().lower() == "airport":
            direction = "Pickup from Airport"
            suburb = original_end_point
            start_point = ''
            end_point = ''
        elif str(original_end_point).strip().lower() == "airport":
            direction = "Drop off to Airport"
            suburb = original_start_point
            start_point = ''
            end_point = ''

        baggage_str = parse_baggage(request)

        p = Inquiry(
            name=name, contact=contact, email=email, pickup_date=pickup_date_obj,
            flight_number=flight_number, flight_time=flight_time, pickup_time=pickup_time,
            direction=direction, suburb=suburb, street=street,
            start_point=start_point, end_point=end_point,
            no_of_passenger=no_of_passenger, no_of_baggage=baggage_str,
            message=message
        )
        p.region = post_region
        p.save()

        ip = get_client_ip(request)
        ip_info = get_ip_info(ip)
        asyncio.run(send_telegram_notification(
            f"✈️ Home Inquiry:\n"
            f"IP: `{ip}`\n"
            f"Location: {ip_info}"
        ))

        return render_inquiry_done(request)

    else:
        return redirect('basecamp:home')
    
