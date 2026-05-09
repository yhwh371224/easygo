import logging

from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from blog.models import Post, Inquiry, Driver
from blog.blog_utils import get_default_driver_for_region, resolve_driver
from regions.models import Region
from basecamp.basecamp_utils import (
    is_ajax, parse_baggage, parse_date,
    to_bool, verify_turnstile,
    render_inquiry_done, booking_success_response, require_turnstile,
    is_duplicate_submission, parse_booking_dates, get_client_ip,
)
from django_ratelimit.decorators import ratelimit
import asyncio
from utils.telegram import send_telegram_notification, get_ip_info

logger = logging.getLogger(__name__)

from regions.models import RequestLog


def _get_request_region(request):
    """URL 접두사에서 감지된 Region을 반환. 없으면 None."""
    region = getattr(request, 'region', None)
    if isinstance(region, Region):
        return region
    return None


# airport booking by client
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_turnstile
def booking_detail(request):
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
            f"[BOOKING] IP={get_client_ip(request)} "
            f"path={request.path} "
            f"email={request.POST.get('email')}"
        )

        # Region selection is mandatory (no default region).
        if not post_region:
            if is_ajax(request):
                return JsonResponse({'success': False, 'message': 'Region is required. Please select your city and try again.'}, status=400)
            return render(request, '400.html', status=400)
        pickup_date_str = request.POST.get('pickup_date', '')
        return_pickup_date_str = request.POST.get('return_pickup_date', '')
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
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

        try:
            pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date_str, return_pickup_date_str)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        # ✅ 중복 제출 방지
        if is_duplicate_submission(Post, email):
            return JsonResponse({'success': False, 'message': 'Duplicate form recently submitted. Please wait before trying again.'})  
            
        driver = get_default_driver_for_region(post_region)

        if not driver and post_region:
            sydney_region = Region.objects.filter(slug='sydney', is_active=True).first()
            if sydney_region:
                driver = get_default_driver_for_region(sydney_region)

        if not driver:
            logger.error(f"No default driver found for region: {post_region} or sydney fallback")
            return JsonResponse({'success': False, 'message': 'Service unavailable. Please contact us directly.'})

        # 🧳 개별 수하물 항목 수집
        baggage_str = parse_baggage(request)

        p = Post(name=name, contact=contact, email=email, pickup_date=pickup_date_obj, flight_number=flight_number, flight_time=flight_time,
                 pickup_time=pickup_time, start_point=start_point, end_point=end_point, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=baggage_str, message=message, return_direction=return_direction,
                 return_pickup_date=return_pickup_date_obj, return_flight_number=return_flight_number, return_flight_time=return_flight_time,
                 return_pickup_time=return_pickup_time, return_start_point=return_start_point, return_end_point=return_end_point, driver=driver,
                 price='TBA', pending=True, reminder=False)
        p.region = post_region
        p.save()

        ip = get_client_ip(request)
        ip_info = get_ip_info(ip)
        try:
            asyncio.run(send_telegram_notification(
                f"✈️ New booking:\n"
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
        return render(request, 'basecamp/booking/booking.html', {
            "region": region,
            "active_regions": active_regions,
        })


# cruise booking by client
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_turnstile
def cruise_booking_detail(request):
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
            f"[BOOKING] IP={get_client_ip(request)} "
            f"path={request.path} "
            f"email={request.POST.get('email')}"
        )

        # ✅ Collect date strings
        pickup_date_str = request.POST.get('pickup_date', '')
        return_pickup_date_str = request.POST.get('return_pickup_date', '')
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        pickup_time = request.POST.get('pickup_time')
        start_point = request.POST.get('start_point', '')
        end_point = request.POST.get('end_point', '')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        message = request.POST.get('message')
        return_pickup_time = request.POST.get('return_pickup_time')
        return_start_point = request.POST.get('return_start_point', '')
        return_end_point = request.POST.get('return_end_point', '')
        price = 'TBA'

        # ✅ 중복 제출 방지
        if is_duplicate_submission(Post, email):
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})

        try:
            pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date_str, return_pickup_date_str)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
        driver = get_default_driver_for_region(post_region)

        if not driver and post_region:
            sydney_region = Region.objects.filter(slug='sydney', is_active=True).first()
            if sydney_region:
                driver = get_default_driver_for_region(sydney_region)

        if not driver:
            logger.error(f"No default driver found for region: {post_region} or sydney fallback")
            return JsonResponse({'success': False, 'message': 'Service unavailable. Please contact us directly.'})

        # 🧳 개별 수하물 항목 수집
        baggage_str = parse_baggage(request)         

        p = Post(name=name, contact=contact, email=email, pickup_date=pickup_date_obj, start_point=start_point,
                 end_point=end_point, pickup_time=pickup_time, price=price,
                 no_of_passenger=no_of_passenger, no_of_baggage=baggage_str,
                 return_pickup_date=return_pickup_date_obj, return_start_point=return_start_point,
                 return_pickup_time=return_pickup_time, return_end_point=return_end_point,
                 message=message, driver=driver, pending=True, reminder=False, region=post_region)

        p.save()

        ip = get_client_ip(request)
        ip_info = get_ip_info(ip)
        try:
            asyncio.run(send_telegram_notification(
                f"🚢 New cruise booking:\n"
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
        return render(request, 'basecamp/booking/cruise_booking.html', {
            "region": region,
            "active_regions": active_regions,
        })


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def confirm_booking_detail(request):
    if request.method == "POST":
        logger.info(
            f"[BOOKING] IP={get_client_ip(request)} "
            f"path={request.path} "
            f"email={request.POST.get('email')}"
        )
        
        honeypot = request.POST.get('phone_verify', '')
        if honeypot != '':
            return JsonResponse({'success': False, 'error': 'Bot detected.'})
        email = request.POST.get('email')
        is_confirmed = request.POST.get('is_confirmed') == 'True'

        index = request.POST.get('index_visible') or request.POST.get('index', '1')
        try:
            index = int(index) - 1
        except ValueError:
            return HttpResponse("Invalid index value", status=400)

        cash = request.POST.get('cash') == 'on'
        prepay = request.POST.get('prepay') == 'on'

        users = Inquiry.objects.filter(booker_email__iexact=email)
        if not users.exists():
            users = Inquiry.objects.filter(email__iexact=email)

        if users.exists() and 0 <= index < len(users):
            user = users[index]
        else:
            return render(request, 'basecamp/email/email_error_confirmbooking.html')

        # 기존 데이터
        name = user.name
        booker_name = user.booker_name
        booer_email = user.booker_email
        contact = user.contact
        company_name = user.company_name
        email1 = user.email1
        pickup_date = user.pickup_date
        flight_number = getattr(user, 'flight_number', "")
        flight_time = getattr(user, 'flight_time', "")
        pickup_time = user.pickup_time
        direction = user.direction
        suburb = user.suburb
        street = user.street
        start_point = getattr(user, 'start_point', "")
        end_point = getattr(user, 'end_point', "")
        no_of_passenger = user.no_of_passenger
        no_of_baggage = user.no_of_baggage
        return_direction = getattr(user, 'return_direction', "")
        return_pickup_date = getattr(user, 'return_pickup_date', "")
        return_flight_number = getattr(user, 'return_flight_number', "")
        return_flight_time = getattr(user, 'return_flight_time', "")
        return_pickup_time = getattr(user, 'return_pickup_time', "")
        return_start_point = getattr(user, 'return_start_point', "")
        return_end_point = getattr(user, 'return_end_point', "")
        cruise = user.cruise
        message = user.message
        notice = user.notice
        price = user.price
        toll = user.toll
        fuel_surcharge = user.fuel_surcharge
        paid = user.paid
        private_ride = user.private_ride
        region = user.region 

        try:
            pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date, return_pickup_date)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        # 최종 가격 계산
        if price in [None, ""]:
            final_price = "TBA"
            toll_value = ""
            fuel_surcharge_value = ""
        else:
            try:
                final_price = float(price)
                if toll:
                    final_price += float(toll)
                if fuel_surcharge:
                    final_price += float(fuel_surcharge)
            except Exception:
                final_price = price
            toll_value = "toll included" if toll else ""
            fuel_surcharge_value = "fs included" if fuel_surcharge else ""

        # pending 상태 결정
        if paid or cash or prepay:
            pending = False
        else:
            pending = True  

        driver = get_default_driver_for_region(region)

        if not driver:
            sydney_region = Region.objects.filter(slug='sydney', is_active=True).first()
            if sydney_region:
                driver = get_default_driver_for_region(sydney_region)

        if not driver:
            logger.error(f"No default driver found for region: {region} or sydney fallback")
            return JsonResponse({'success': False, 'message': 'Service unavailable. Please contact us directly.'})

        is_confirmed = False  

        # Post 모델 저장
        p = Post(
            name=name, contact=contact, email=email, company_name=company_name, email1=email1,
            pickup_date=pickup_date_obj, flight_number=flight_number, flight_time=flight_time, pickup_time=pickup_time,
            direction=direction, suburb=suburb, street=street, start_point=start_point, end_point=end_point,
            cruise=cruise, no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage,
            return_direction=return_direction, private_ride=private_ride,
            return_pickup_date=return_pickup_date_obj, return_flight_number=return_flight_number,
            return_flight_time=return_flight_time, return_pickup_time=return_pickup_time,
            return_start_point=return_start_point, return_end_point=return_end_point,
            message=message, notice=notice, price=final_price, toll=toll_value,
            fuel_surcharge=fuel_surcharge_value, prepay=prepay, pending=pending,
            paid=paid, cash=cash, is_confirmed=is_confirmed, driver=driver, region=region,
        )

        p.save()

        user.delete()

        ip = get_client_ip(request)
        ip_info = get_ip_info(ip)
        asyncio.run(send_telegram_notification(
            f"Clicked the confirm button:\n"
            f"IP: `{ip}`\n"
            f"Location: {ip_info}"
        ))

        return render_inquiry_done(request)

    else:
        return render(request, 'basecamp/booking/confirm_booking.html', {})

# For Return Trip
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_turnstile
def return_trip_detail(request):
    if request.method == "POST":
        logger.info(
            f"[BOOKING] IP={get_client_ip(request)} "
            f"path={request.path} "
            f"email={request.POST.get('email')}"
        )
        
        pickup_date_str = request.POST.get('pickup_date', '')
        return_pickup_date_str = request.POST.get('return_pickup_date', '')
        email = request.POST.get('email', '').strip()
        flight_number = request.POST.get('flight_number', '')
        flight_time = request.POST.get('flight_time', '')
        pickup_time = request.POST.get('pickup_time', '')
        start_point = request.POST.get('start_point', '')
        end_point = request.POST.get('end_point', '')
        direction = request.POST.get('direction', '')
        message = request.POST.get('message', '')
        notice = request.POST.get('notice', '')
        price = request.POST.get('price', '')
        toll = request.POST.get('toll', '')
        fuel_surcharge = request.POST.get('fuel_surcharge', '')
        cash = to_bool(request.POST.get('cash', ''))
        prepay = to_bool(request.POST.get('prepay', ''))
        return_direction = request.POST.get('return_direction', '')
        return_flight_number = request.POST.get('return_flight_number', '')
        return_flight_time = request.POST.get('return_flight_time', '')
        return_pickup_time = request.POST.get('return_pickup_time', '')
        return_start_point = request.POST.get('return_start_point', '')
        return_end_point = request.POST.get('return_end_point', '') 
        
        user = Post.objects.filter(Q(email__iexact=email)).first()    
        
        if not user:
            return render(request, '403.html')    
            
        else:
            name = user.name     
            company_name = user.company_name       
            contact = user.contact
            suburb = user.suburb
            street = user.street
            no_of_passenger = user.no_of_passenger
            no_of_baggage = user.no_of_baggage   
            region = user.region         
            if not start_point:
                start_point = user.start_point
            if not end_point:
                end_point = user.end_point
            
            # message 추가 (기존 내용 보존)
            if message and user.message:
                message = f"{user.message} | {message}"
            elif not message:
                message = user.message

            # notice 추가 (기존 내용 보존)
            if notice and user.notice:
                notice = f"{user.notice} | {notice}"
            elif not notice:
                notice = user.notice

            # 날짜 파싱
            try:
                pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date_str, return_pickup_date_str)
            except ValueError as e:
                return JsonResponse({'success': False, 'error': str(e)})

        # ✅ 중복 제출 방지
        if is_duplicate_submission(Post, email):
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})
         
        driver = resolve_driver(suburb)

        if not driver:
            driver = get_default_driver_for_region(region)

        if not driver:
            sydney_region = Region.objects.filter(slug='sydney', is_active=True).first()
            if sydney_region:
                driver = get_default_driver_for_region(sydney_region)

        if not driver:
            logger.error(f"No default driver found for suburb: {suburb}, region: {region}")
            return JsonResponse({'success': False, 'message': 'Service unavailable. Please contact us directly.'})  
                    
        p = Post(name=name, company_name=company_name, contact=contact, email=email, pickup_date=pickup_date_obj, flight_number=flight_number, flight_time=flight_time,
                 pickup_time=pickup_time, start_point=start_point, end_point=end_point, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, cash=cash, prepay=prepay, return_direction=return_direction,
                 return_pickup_date=return_pickup_date_obj, return_flight_number=return_flight_number, return_flight_time=return_flight_time,
                 return_pickup_time=return_pickup_time, return_start_point=return_start_point, return_end_point=return_end_point, driver=driver,
                 price=price, toll=toll, fuel_surcharge=fuel_surcharge, region=region)

        p.save()

        return JsonResponse({'success': True, 'redirect_url': '/inquiry_done/'})
    
    else:
        return render(request, 'basecamp/booking/return_trip.html', {}) 