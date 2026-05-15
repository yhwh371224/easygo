import asyncio
import logging

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from basecamp.views.inquirys import _get_request_region
from django_ratelimit.decorators import ratelimit
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
from utils.telegram import send_telegram_notification, get_ip_info

logger = logging.getLogger(__name__)

from regions.models import RequestLog


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_POST
def confirm_booking_detail(request):
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
    special_items = user.special_items or {}
    extra_stop = user.extra_stop or 0
    extra_stop_addresses = user.extra_stop_addresses or []
    same_extra_stop = user.same_extra_stop

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
        special_items=special_items, extra_stop=extra_stop, extra_stop_addresses=extra_stop_addresses,
        same_extra_stop=same_extra_stop,
    )

    p.save()

    user.delete()

    ip = get_client_ip(request)
    ip_info = get_ip_info(ip)
    try:
        asyncio.run(send_telegram_notification(
            f"Clicked the confirm button:\n"
            f"IP: `{ip}`\n"
            f"Location: {ip_info}"
        ))
    except Exception as e:
        logger.error(f"[TELEGRAM] Failed to send: {e}")

    return render_inquiry_done(request)

# For Return Trip
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_POST
@require_turnstile
def return_trip_detail(request):
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

    # ✅ 중복 제출 방지
    if is_duplicate_submission(Post, email):
        return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})
    
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
        extra_stop = user.extra_stop or 0
        same_extra_stop = user.same_extra_stop
        extra_stop_addresses = user.extra_stop_addresses if same_extra_stop else []
        special_items = user.special_items or {}
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
                price=price, toll=toll, fuel_surcharge=fuel_surcharge, region=region,
                extra_stop=extra_stop, same_extra_stop=same_extra_stop, extra_stop_addresses=extra_stop_addresses,
                special_items=special_items)

    p.save()

    return JsonResponse({'success': True, 'redirect_url': '/inquiry_done/'})



# STEP 1 — POST from home tab
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_POST
def quick_rebook_step1(request, region_slug=None):
    email         = request.POST.get('email', '').strip()
    pickup_date   = request.POST.get('pickup_date', '').strip()
    flight_number = request.POST.get('flight_number', '').strip()
    pickup_time   = request.POST.get('pickup_time', '').strip()

    def render_step1_error(msg):
        request.session['rebook_error'] = msg
        region = _get_request_region(request)
        if region:
            return redirect(f'/{region.slug}/')
        return redirect('basecamp:home')

    if not email:
        return render_step1_error('Please enter your email address.')

    if not pickup_date:
        return render_step1_error('Please select a pickup date.')

    try:
        pickup_date_obj = parse_date(pickup_date, field_name='Pickup Date', required=True)
    except ValueError as e:
        return render_step1_error(str(e))

    previous = Post.objects.filter(
        email__iexact=email,
        cancelled=False,
    ).first()

    if not previous:
        request.session['rebook_error'] = (
            'No previous booking found for this email. '
            'Please use New Booking.'
        )
        region = _get_request_region(request)
        if region:
            return redirect(f'/{region.slug}/')
        return redirect('basecamp:home')

    logger.info(f"[QUICK REBOOK STEP1] email={email} found previous Post id={previous.id}")

    return render(request, 'basecamp/quick_rebook_step2.html', {
        'previous'       : previous,
        'email'          : email,
        'pickup_date'    : pickup_date,
        'pickup_date_obj': pickup_date_obj,
        'flight_number'  : flight_number,
        'pickup_time'    : pickup_time,
        'active_regions' : Region.objects.filter(is_active=True),
        'error'          : None,
    })


# STEP 2 — POST from quick_rebook_step2.html form submission
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_POST
@require_turnstile
def quick_rebook_confirm(request, region_slug=None):

    # 1. Step 1 에서 넘어온 값
    email           = request.POST.get('email', '').strip()
    pickup_date_str = request.POST.get('pickup_date', '').strip()
    flight_number   = request.POST.get('flight_number', '').strip()
    pickup_time     = request.POST.get('pickup_time', '').strip()

    # 2. Step 2 폼에서 받는 값 (수정 가능)
    contact         = request.POST.get('contact', '').strip()
    no_of_passenger = request.POST.get('no_of_passenger', '').strip()
    no_of_baggage   = request.POST.get('no_of_baggage', '').strip()
    direction       = request.POST.get('direction', '').strip()
    suburb          = request.POST.get('suburb', '').strip()
    flight_time     = request.POST.get('flight_time', '').strip()
    message         = request.POST.get('message', '').strip()

    # Return trip
    has_return           = request.POST.get('has_return') == 'on'
    return_date_str      = request.POST.get('return_pickup_date', '').strip()
    return_flight_number = request.POST.get('return_flight_number', '').strip()
    return_flight_time   = request.POST.get('return_flight_time', '').strip()
    return_pickup_time   = request.POST.get('return_pickup_time', '').strip()

    # 중복 제출 방지
    if is_duplicate_submission(Post, email):
        return render(request, 'basecamp/quick_rebook_step2.html', {
            'error': 'Duplicate submission. Please wait a moment and try again.',
        })
    
    # 3. DB에서 직접 조회 — 안전하고 정확
    previous = Post.objects.filter(email__iexact=email, cancelled=False).first()
    if not previous:
        return redirect('basecamp:home')

    previous_name  = previous.name
    previous_price = previous.price
    region         = previous.region
    extra_stop     = int(request.POST.get('extra_stop') or previous.extra_stop or 0)
    same_extra_stop = request.POST.get('same_extra_stop') == '1'
    extra_stop_addresses = [
        a for i in range(1, extra_stop + 1)
        if (a := request.POST.get(f'extra_stop_address_{i}', '').strip())
    ]
    if not extra_stop_addresses and same_extra_stop:
        extra_stop_addresses = previous.extra_stop_addresses
    special_items  = previous.special_items or {}

    # Driver 배정
    driver = resolve_driver(suburb)
    if not driver:
        driver = get_default_driver_for_region(region)
    if not driver:
        sydney_region = Region.objects.filter(slug='sydney', is_active=True).first()
        if sydney_region:
            driver = get_default_driver_for_region(sydney_region)
    if not driver:
        logger.error(f"[QUICK REBOOK] No driver found for suburb={suburb}, region={region}")

    # 날짜 파싱
    try:
        pickup_date_obj = parse_date(pickup_date_str, field_name='Pickup Date', required=True)
    except ValueError as e:
        return render(request, 'basecamp/quick_rebook_step2.html', {'error': str(e)})

    return_date_obj = None
    if has_return and return_date_str:
        try:
            return_date_obj = parse_date(return_date_str, field_name='Return Date', required=False)
        except ValueError:
            return_date_obj = None

    # Post 저장
    p = Post(
        name            = previous_name,
        contact         = contact,
        email           = email,
        pickup_date     = pickup_date_obj,
        flight_number   = flight_number,
        flight_time     = flight_time,
        pickup_time     = pickup_time,
        direction       = direction,
        suburb          = suburb,
        no_of_passenger = no_of_passenger,
        no_of_baggage   = no_of_baggage,
        message         = message,
        region          = region,
        price           = previous_price,
        pending         = True,
        driver          = driver,
        return_pickup_date   = return_date_obj if has_return else None,
        return_flight_number = return_flight_number if has_return else '',
        return_flight_time   = return_flight_time if has_return else '',
        return_pickup_time   = return_pickup_time if has_return else '',
        return_direction     = 'Pickup from Intl Airport' if has_return else '',
        extra_stop           = extra_stop,
        same_extra_stop      = same_extra_stop,
        extra_stop_addresses = extra_stop_addresses,
        special_items        = special_items,
    )
    p.save()

    # 이전 Post cancelled 처리 (DB 기록 보존)
    previous.cancelled = True
    previous.save(update_fields=['cancelled'])

    logger.info(f"[QUICK REBOOK CONFIRM] Post id={p.id} email={email} date={pickup_date_str}")

    ip      = get_client_ip(request)
    ip_info = get_ip_info(ip)
    try:
        asyncio.run(send_telegram_notification(
            f"🔄 Quick Rebook:\n"
            f"IP: `{ip}`\n"
            f"Location: {ip_info}"
        ))
    except Exception as e:
        logger.error(f"[TELEGRAM] Quick Rebook failed: {e}")

    return booking_success_response(request)