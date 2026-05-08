import asyncio
import logging

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django_ratelimit.decorators import ratelimit

from regions.models import Region, RequestLog
from blog.models import Inquiry
from basecamp.basecamp_utils import (
    require_turnstile, is_duplicate_submission,
    booking_success_response, parse_baggage, parse_booking_dates,
    get_client_ip,
)
from utils.telegram import get_ip_info, send_telegram_notification

logger = logging.getLogger(__name__)


def region_inquiry(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')
    return render(request, 'regions/inquiry/inquiry.html', {
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

        if is_duplicate_submission(Inquiry, email, region_slug=region_slug):
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

        ip = get_client_ip(request)
        ip_info = get_ip_info(ip)
        asyncio.run(send_telegram_notification(
            f"✈️ New inquiry:\n"
            f"IP: `{ip}`\n"
            f"Location: {ip_info}"
        ))
        return booking_success_response(request)

    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')
    return render(request, 'regions/inquiry/inquiry.html', {'region': region, 'suburbs': suburbs})

