import asyncio
from django.shortcuts import render, redirect
from django.http import JsonResponse
from blog.models import Inquiry
from regions.models import Region
from basecamp.basecamp_utils import (
    is_ajax, parse_baggage, parse_date, handle_email_sending,
    verify_turnstile,
    render_inquiry_done, booking_success_response, require_turnstile,
    is_duplicate_submission, parse_booking_dates, get_customer_status,
)
from django_ratelimit.decorators import ratelimit
from utils.telegram import send_telegram_notification


def _get_request_region(request):
    """URL 접두사에서 감지된 Region을 반환. 없으면 Sydney 기본값."""
    region = getattr(request, 'region', None)
    if isinstance(region, Region):
        return region
    try:
        return Region.objects.get(slug='sydney')
    except Region.DoesNotExist:
        return None


# Inquiry for airport
@ratelimit(key='ip', rate='5/m', method='POST', block=False)
@require_turnstile
def inquiry_details(request):
    if request.method == "POST":
        if getattr(request, 'limited', False):
            if is_ajax(request):
                return JsonResponse({'success': False, 'message': 'Too many requests. Please wait a moment and try again.'}, status=429)
            return render(request, 'basecamp/403.html', status=429)
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
            return_end_point=return_end_point, message=message
        )
        p.region = _get_request_region(request)
        p.save()

        asyncio.run(send_telegram_notification("✈️ New inquiry has been received."))

        return booking_success_response(request)

    else:
        return render(request, 'basecamp/booking/inquiry.html', {})


# inquiry (simple one) for airport from home page
@ratelimit(key='ip', rate='5/m', method='POST', block=False)
@require_turnstile
def inquiry_details1(request):
    if request.method == "POST":
        if getattr(request, 'limited', False):
            if is_ajax(request):
                return JsonResponse({'success': False, 'message': 'Too many requests. Please wait a moment and try again.'}, status=429)
            return render(request, 'basecamp/403.html', status=429)
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
        
        original_start_point = request.session.get('original_start_point', start_point)
        original_end_point = request.session.get('original_end_point', end_point)
        
        direction = ""
        suburb = ""

        try:
            pickup_date_obj = parse_date(pickup_date_str, field_name="Pickup Date", required=True)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        if is_duplicate_submission(Inquiry, email):
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})

        if original_start_point == "Sydney Int'l Airport":
            direction = 'Pickup from Intl Airport'
            suburb = original_end_point
            start_point = ''
            end_point = ''
        elif original_start_point == "Sydney Domestic Airport":
            direction = 'Pickup from Domestic Airport'
            suburb = original_end_point
            start_point = ''
            end_point = ''
        elif original_end_point == "Sydney Int'l Airport":
            direction = 'Drop off to Intl Airport'
            suburb = original_start_point
            end_point = ''
            start_point = ''
        elif original_end_point == "Sydney Domestic Airport":
            direction = 'Drop off to Domestic Airport'
            suburb = original_start_point
            end_point = ''
            start_point = ''

        baggage_str = parse_baggage(request)

        p = Inquiry(
            name=name, contact=contact, email=email, pickup_date=pickup_date_obj,
            flight_number=flight_number, flight_time=flight_time, pickup_time=pickup_time,
            direction=direction, suburb=suburb, street=street,
            start_point=start_point, end_point=end_point,
            no_of_passenger=no_of_passenger, no_of_baggage=baggage_str,
            message=message
        )
        p.region = _get_request_region(request)
        p.save()

        asyncio.run(send_telegram_notification("🏠 Inquiry home page has been received."))

        return render_inquiry_done(request)

    else:
        return redirect('basecamp:home')
    

# Multiple points Inquiry
@ratelimit(key='ip', rate='5/m', method='POST', block=False)
@require_turnstile
def p2p_detail(request):
    if request.method == "POST":
        if getattr(request, 'limited', False):
            if is_ajax(request):
                return JsonResponse({'success': False, 'message': 'Too many requests. Please wait a moment and try again.'}, status=429)
            return render(request, 'basecamp/403.html', status=429)
        p2p_name = request.POST.get('p2p_name')
        p2p_phone = request.POST.get('p2p_phone')
        p2p_email = request.POST.get('p2p_email')
        p2p_date = request.POST.get('p2p_date')
        first_pickup_location = request.POST.get('first_pickup_location')
        first_putime = request.POST.get('first_putime')
        first_dropoff_location = request.POST.get('first_dropoff_location')
        second_pickup_location = request.POST.get('second_pickup_location')
        second_putime = request.POST.get('second_putime')
        second_dropoff_location = request.POST.get('second_dropoff_location')
        third_pickup_location = request.POST.get('third_pickup_location')
        third_putime = request.POST.get('third_putime')
        third_dropoff_location = request.POST.get('third_dropoff_location')
        fourth_pickup_location = request.POST.get('fourth_pickup_location')
        fourth_putime = request.POST.get('fourth_putime')
        fourth_dropoff_location = request.POST.get('fourth_dropoff_location')
        p2p_passengers = request.POST.get('p2p_passengers')
        p2p_baggage = request.POST.get('p2p_baggage')
        p2p_message = request.POST.get('p2p_message')

        # ✅ 중복 제출 방지
        if is_duplicate_submission(Inquiry, p2p_email):
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})  

        subject = "Multiple points inquiry"
        template_name = "html_email-p2p.html"

        context = {
            'p2p_name': p2p_name, 'p2p_phone': p2p_phone, 'p2p_email': p2p_email, 'p2p_date': p2p_date, 
            'first_pickup_location': first_pickup_location, 'first_putime': first_putime, 'first_dropoff_location': first_dropoff_location, 
            'second_pickup_location': second_pickup_location, 'second_putime': second_putime, 'second_dropoff_location': second_dropoff_location, 
            'third_pickup_location': third_pickup_location, 'third_putime': third_putime, 'third_dropoff_location': third_dropoff_location, 
            'fourth_pickup_location': fourth_pickup_location, 'fourth_putime': fourth_putime, 'fourth_dropoff_location': fourth_dropoff_location, 
            'p2p_passengers': p2p_passengers, 'p2p_baggage': p2p_baggage, 'p2p_message': p2p_message,
        }

        handle_email_sending(request, p2p_email, subject, template_name, context)
        
        return booking_success_response(request)

    else:
        return render(request, 'basecamp/booking/p2p.html', {})