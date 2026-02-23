from datetime import datetime, date, timedelta

import logging
import requests
import stripe
import json 

from django.conf import settings
from csp.constants import NONCE
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.utils import timezone

from main.settings import RECIPIENT_EMAIL, DEFAULT_FROM_EMAIL
from blog.models import Post, Inquiry, PaypalPayment, StripePayment, Driver
from blog.tasks import send_confirm_email
from blog.sms_utils import send_sms_notice, send_whatsapp_template
from basecamp.area import get_suburbs
from basecamp.area_full import get_more_suburbs
from basecamp.area_home import get_home_suburbs
from basecamp.area_zones import area_zones

from .utils import (
    is_ajax, parse_date, handle_email_sending, format_pickup_time_12h,
    render_to_pdf, add_bag, to_int, to_bool, safe_float,
    handle_checkout_session_completed, paypal_ipn_error_email, get_sorted_suburbs,
    verify_turnstile, render_email_template
)


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


def about_us(request): 
    # send_notice_email.delay('about_us accessed', 'about_us accessed', RECIPIENT_EMAIL)
    return render(request, 'basecamp/pages/about_us.html')


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
    }

    return render(request, 'basecamp/pillars/airport-maxi-taxi.html', context)


# Suburb names
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


def arrival_guide(request): 
    return render(request, 'basecamp/pages/arrival_guide.html')


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


def confirmation_multiplebookings(request): 
    return render(request, 'basecamp/confirmation_multiplebookings.html')


def confirm_booking(request): 
    return render(request, 'basecamp/booking/confirm_booking.html')


def contact_form(request):
    return render(request, 'basecamp/pages/contact_form.html')


def cruise_booking(request):
    return render(request, 'basecamp/booking/cruise_booking.html')


def cruise_inquiry(request):
    return render(request, 'basecamp/booking/cruise_booking.html')


def error(request): 
    return render(request, 'basecamp/error/error.html')


def email_dispatch(request): 
    return render(request, 'basecamp/email/email_dispatch.html')


def email_error_confirmbooking(request): 
    return render(request, 'basecamp/email/email_error_confirmbooking.html')


def home_error(request): 
    return render(request, 'basecamp/error/home_error.html')


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


def inquiry_done(request):
    return render(request, 'basecamp/inquiry_done.html', {
        'google_review_url': settings.GOOGLE_REVIEW_URL,
    })


def information(request): 
    return render(request, 'basecamp/pages/information.html')


def invoice(request): 
    return render(request, 'basecamp/invoice.html')


def invoice_details(request): 
    return render(request, 'basecamp/invoice_details.html')


def meeting_point(request): 
    return render(request, 'basecamp/pages/meeting_point.html')


def more_suburbs(request): 
    more_suburbs = get_more_suburbs()
    return render(request, 'basecamp/layouts/more_suburbs.html', {'more_suburbs': more_suburbs})


def more_suburbs1(request): 
    more_suburbs = get_more_suburbs()
    return render(request, 'basecamp/layouts/more_suburbs1.html', {'more_suburbs': more_suburbs})


def more_suburbs_maxi_taxi(request):
    more_suburbs = get_more_suburbs()
    return render(request, 'basecamp/layouts/more_suburbs_maxi_taxi.html', {'more_suburbs': more_suburbs})


def payment_cancel(request): 
    return render(request, 'basecamp/payments/payment_cancel.html')


def payment_options(request):
    return render(request, 'basecamp/payments/payment_options.html')


def payment_options1(request): 
    return render(request, 'basecamp/payments/payment_options1.html')


def payonline(request):
    context = {
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
        'csp_nonce': NONCE, 
    }
    return render(request, 'basecamp/payments/payonline.html', context)


def p2p(request):     
    return render(request, 'basecamp/booking/p2p.html')


def p2p_booking(request):
    return render(request, 'basecamp/booking/p2p_booking.html')


def p2p_single(request):
    return render(request, 'basecamp/booking/p2p_single.html')


def privacy(request):     
    return render(request, 'basecamp/pages/privacy.html')


def return_cruise_fields(request): 
    return render(request, 'basecamp/layouts/return_cruise_fields.html')


def return_flight_fields(request): 
    return render(request, 'basecamp/layouts/return_flight_fields.html')


def return_trip(request): 
    return render(request, 'basecamp/booking/return_trip.html')


def sending_email_first(request): 
    return render(request, 'basecamp/email/sending_email_first.html')


def sending_email_second(request): 
    return render(request, 'basecamp/email/sending_email_second.html')


def sending_email_input_data(request): 
    return render(request, 'basecamp/email/sending_email_input_data.html')


def service(request):     
    return render(request, 'basecamp/pages/service.html')


def success(request): 
    return render(request, 'basecamp/layouts/success.html')


def sydney_airport_shuttle(request):
    return render(request, 'basecamp/pillars/sydney_airport_shuttle.html')


def sydney_airport_transfer(request):
    return render(request, 'basecamp/pillars/sydney_airport_transfer.html')


def sydney_cruise_transfer(request):
    return render(request, 'basecamp/pillars/sydney_cruise_transfer.html')


def terms(request): 
    return render(request, 'basecamp/pages/terms.html')


def wrong_date_today(request): 
    return render(request, 'basecamp/error/wrong_date_today.html')


# Inquiry for airport 
def inquiry_details(request):
    if request.method == "POST":
        token = request.POST.get('cf-turnstile-response', '')
        ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
        if not verify_turnstile(token, ip):
            return JsonResponse({'success': False, 'error': 'Security verification failed. Please try again.'})
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
        recent_duplicate = Inquiry.objects.filter(
            email=email,
            created__gte=timezone.now() - timedelta(seconds=10)
        ).exists()

        try:
            pickup_date_obj = parse_date(
                pickup_date_str, 
                field_name="Pickup Date", 
                required=True
            )

            return_pickup_date_obj = parse_date(
                return_pickup_date_str, 
                field_name="Return Pickup Date", 
                required=False, 
                reference_date=pickup_date_obj 
            )
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        if recent_duplicate:
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})       

        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'pickup_date': pickup_date_obj.strftime('%Y-%m-%d'),
            'pickup_time': pickup_time,
            'direction': direction,
            'street': street,
            'suburb': suburb,
            'no_of_passenger': no_of_passenger,
            'flight_number': flight_number,
            'flight_time': flight_time,
            'start_point': start_point,
            'end_point': end_point,
            'return_pickup_date': return_pickup_date_obj.strftime('%Y-%m-%d') if return_pickup_date_obj else '',
            'return_flight_number': return_flight_number,
            'return_flight_time': return_flight_time,
            'return_pickup_time': return_pickup_time,
            'return_start_point': return_start_point,
            'return_end_point': return_end_point,
            'message': message
        }
     
        inquiry_email_exists = Inquiry.objects.filter(email=email).exists()
        post_email_exists = Post.objects.filter(email=email).exists()

        email_subject = f"Inquiry on {data['pickup_date']}"

        email_content_template = '''
        Hello, {name} \n
        {status_message}\n 
        https://easygoshuttle.com.au
        =============================
        Contact: {contact}
        Email: {email}  
        ✅ Pickup date: {pickup_date}
        Pickup time: {pickup_time}
        Direction: {direction}
        Street: {street}
        Suburb: {suburb}
        Passenger: {no_of_passenger}
        Flight number: {flight_number}
        Flight time: {flight_time}
        Start Point: {start_point}
        End Point: {end_point}
        ✅ Return Pickup date: {return_pickup_date}
        Return Flight number: {return_flight_number}
        Return Flight time: {return_flight_time}
        Return Pickup time: {return_pickup_time}
        Return Start Point: {return_start_point}
        Return End Point: {return_end_point}
        Message: {message}
        =============================\n        
        Best Regards,
        EasyGo Admin \n\n        
        '''

        if inquiry_email_exists or post_email_exists:
            data['status_message'] = "Exist in Inquiry or Post *"
        else:
            data['status_message'] = "Neither in Inquiry & Post *"
            
        content = email_content_template.format(**data)
        send_mail(email_subject, content, '', [RECIPIENT_EMAIL])

        # 🧳 개별 수하물 항목 수집
        large = to_int(request.POST.get('baggage_large'))
        medium = to_int(request.POST.get('baggage_medium'))
        small = to_int(request.POST.get('baggage_small'))

        baby_seat = to_int(request.POST.get('baggage_baby'))
        booster_seat = to_int(request.POST.get('baggage_booster'))
        pram = to_int(request.POST.get('baggage_pram'))

        ski = to_int(request.POST.get('baggage_ski'))
        snowboard = to_int(request.POST.get('baggage_snowboard'))
        golf = to_int(request.POST.get('baggage_golf'))
        bike = to_int(request.POST.get('baggage_bike'))
        boxes = to_int(request.POST.get('baggage_boxes'))
        musical_instrument = to_int(request.POST.get('baggage_music'))

        # Oversize flags (수량 있을 때만 유효)
        ski_oversize = ski > 0 and request.POST.get('ski_oversize') == 'on'
        snowboard_oversize = snowboard > 0 and request.POST.get('snowboard_oversize') == 'on'
        golf_oversize = golf > 0 and request.POST.get('golf_oversize') == 'on'
        bike_oversize = bike > 0 and request.POST.get('bike_oversize') == 'on'
        boxes_oversize = boxes > 0 and request.POST.get('boxes_oversize') == 'on'
        musical_instrument_oversize = (
            musical_instrument > 0 and request.POST.get('music_oversize') == 'on'
        )

        # 🎯 요약 문자열 생성
        baggage_summary = []

        # Standard luggage
        add_bag(baggage_summary, "L", large)
        add_bag(baggage_summary, "M", medium)
        add_bag(baggage_summary, "S", small)

        # Seats / prams
        add_bag(baggage_summary, "Baby", baby_seat)
        add_bag(baggage_summary, "Booster", booster_seat)
        add_bag(baggage_summary, "Pram", pram)

        # Oversize-capable items
        add_bag(baggage_summary, "Ski", ski, ski_oversize)
        add_bag(baggage_summary, "Snow", snowboard, snowboard_oversize)
        add_bag(baggage_summary, "Golf", golf, golf_oversize)
        add_bag(baggage_summary, "Bike", bike, bike_oversize)
        add_bag(baggage_summary, "Box", boxes, boxes_oversize)
        add_bag(baggage_summary, "Music", musical_instrument, musical_instrument_oversize)

        baggage_str = ", ".join(baggage_summary)
                    
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
        
        p.save()

        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})        
        else:
            return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })
        
    else:
        return render(request, 'basecamp/booking/inquiry.html', {})


# inquiry (simple one) for airport from home page
def inquiry_details1(request):
    if request.method == "POST":
        token = request.POST.get('cf-turnstile-response', '')
        ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
        if not verify_turnstile(token, ip):
            return JsonResponse({'success': False, 'error': 'Security verification failed. Please try again.'})
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

        # ✅ 날짜 파싱 및 유효성 검증 
        try:
            pickup_date_obj = parse_date(
                pickup_date_str, 
                field_name="Pickup Date", 
                required=True
            )

        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        # ✅ 중복 제출 방지 
        recent_duplicate = Inquiry.objects.filter(
            email=email,
            created__gte=timezone.now() - timedelta(seconds=2)
        ).exists()

        if recent_duplicate:
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})

        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'pickup_date': pickup_date_obj.strftime('%Y-%m-%d'),
            'flight_number': flight_number,
            'pickup_time': pickup_time,
            'start_point': start_point,
            'end_point': end_point,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'message': message, 
            'status_message': '' 
        }
     
        inquiry_email_exists = Inquiry.objects.filter(email=email).exists()
        post_email_exists = Post.objects.filter(email=email).exists()
        
        # 3. 이메일 템플릿 (키워드 기반 포맷팅으로 통일)
        email_content_template = '''
        Hello, {name} \n
        {status_message}\n 
        *** It starts from Home Page
        =============================
        Contact: {contact}
        Email: {email}  
        ✅ Pickup date: {pickup_date}
        Flight number: {flight_number}
        Pickup time: {pickup_time}
        start_point: {start_point}
        Street: {street}
        end_point: {end_point}
        Passenger: {no_of_passenger}
        Message: {message}
        =============================\n        
        Best Regards,
        EasyGo Admin \n\n        
        '''

        if inquiry_email_exists or post_email_exists:
            data['status_message'] = "✅ Exist in Inquiry or Post *"
        else:
            data['status_message'] = "Neither in Inquiry & Post *"
            
        content = email_content_template.format(**data)
        
        email_subject = f"Inquiry on {data['pickup_date']} - {data['name']}"
        send_mail(email_subject, content, '', [RECIPIENT_EMAIL])

        if original_start_point == "Sydney Int'l Airport":
            direction = 'Pickup from Intl Airport'
            suburb = original_end_point # end_point 대신 original_end_point 사용
            start_point = ''
            end_point = ''
        elif original_start_point == "Sydney Domestic Airport":
            direction = 'Pickup from Domestic Airport'
            suburb = original_end_point # end_point 대신 original_end_point 사용
            start_point = ''
            end_point = ''
        elif original_end_point == "Sydney Int'l Airport":
            direction = 'Drop off to Intl Airport'
            suburb = original_start_point # start_point 대신 original_start_point 사용
            end_point = ''
            start_point = ''
        elif original_end_point == "Sydney Domestic Airport":
            direction = 'Drop off to Domestic Airport'
            suburb = original_start_point # start_point 대신 original_start_point 사용
            end_point = ''
            start_point = ''
        
        # 🧳 개별 수하물 항목 수집
        large = to_int(request.POST.get('baggage_large'))
        medium = to_int(request.POST.get('baggage_medium'))
        small = to_int(request.POST.get('baggage_small'))

        baby_seat = to_int(request.POST.get('baggage_baby'))
        booster_seat = to_int(request.POST.get('baggage_booster'))
        pram = to_int(request.POST.get('baggage_pram'))

        ski = to_int(request.POST.get('baggage_ski'))
        snowboard = to_int(request.POST.get('baggage_snowboard'))
        golf = to_int(request.POST.get('baggage_golf'))
        bike = to_int(request.POST.get('baggage_bike'))
        boxes = to_int(request.POST.get('baggage_boxes'))
        musical_instrument = to_int(request.POST.get('baggage_music'))

        # Oversize flags (수량 있을 때만 유효)
        ski_oversize = ski > 0 and request.POST.get('ski_oversize') == 'on'
        snowboard_oversize = snowboard > 0 and request.POST.get('snowboard_oversize') == 'on'
        golf_oversize = golf > 0 and request.POST.get('golf_oversize') == 'on'
        bike_oversize = bike > 0 and request.POST.get('bike_oversize') == 'on'
        boxes_oversize = boxes > 0 and request.POST.get('boxes_oversize') == 'on'
        musical_instrument_oversize = (
            musical_instrument > 0 and request.POST.get('music_oversize') == 'on'
        )

        # 🎯 요약 문자열 생성
        baggage_summary = []

        # Standard luggage
        add_bag(baggage_summary, "L", large)
        add_bag(baggage_summary, "M", medium)
        add_bag(baggage_summary, "S", small)

        # Seats / prams
        add_bag(baggage_summary, "Baby", baby_seat)
        add_bag(baggage_summary, "Booster", booster_seat)
        add_bag(baggage_summary, "Pram", pram)

        # Oversize-capable items
        add_bag(baggage_summary, "Ski", ski, ski_oversize)
        add_bag(baggage_summary, "Snow", snowboard, snowboard_oversize)
        add_bag(baggage_summary, "Golf", golf, golf_oversize)
        add_bag(baggage_summary, "Bike", bike, bike_oversize)
        add_bag(baggage_summary, "Box", boxes, boxes_oversize)
        add_bag(baggage_summary, "Music", musical_instrument, musical_instrument_oversize)

        baggage_str = ", ".join(baggage_summary)
        
        p = Inquiry(
            name=name, contact=contact, email=email, pickup_date=pickup_date_obj,  
            flight_number=flight_number, flight_time=flight_time, pickup_time=pickup_time, 
            direction=direction, suburb=suburb, street=street,
            start_point=start_point, end_point=end_point, 
            no_of_passenger=no_of_passenger, no_of_baggage=baggage_str, 
            message=message
        )
        
        p.save()

        return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })

    else:
        return redirect('basecamp:home')


# Contact form
def contact_submit(request):
    if request.method == "POST":
        token = request.POST.get('cf-turnstile-response', '')
        ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
        if not verify_turnstile(token, ip):
            return JsonResponse({'success': False, 'error': 'Security verification failed. Please try again.'})
        # --- Honeypot check ---
        website_honeypot = request.POST.get("website", "")
        if website_honeypot:  # 봇이 채우면 무효
            if is_ajax(request):
                return JsonResponse({'success': False, 'error': 'Spam detected.'})
            else:
                return render(request, 'basecamp/spam_detected.html')  # 간단한 페이지

        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        pickup_date = request.POST.get('pickup_date')
        message = request.POST.get('message')

        today = date.today()
        if pickup_date != str(today):
            if is_ajax(request):
                return render(request, 'basecamp/error/wrong_date_today.html')
            else:
                return render(request, 'basecamp/error/wrong_date_today.html')

        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'pickup_date': pickup_date,
            'message': message}       
                     
        message_template = '''
        Contact Form
        =====================
        name: {name}
        contact: {contact}        
        email: {email}
        Pickup date: {pickup_date}
        message: {message}              
        '''
        message = message_template.format(**data)

        subject = f"[New Contact] Submission from {data['name']}"

        send_mail(subject, message, '', [RECIPIENT_EMAIL])
        
        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
        else:
            return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })
    else:
        return render(request, 'basecamp/pages/contact_form.html', {})
    
    
# Multiple points Inquiry 
def p2p_detail(request):
    if request.method == "POST":
        token = request.POST.get('cf-turnstile-response', '')
        ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
        if not verify_turnstile(token, ip):
            return JsonResponse({'success': False, 'error': 'Security verification failed. Please try again.'})
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
        recent_duplicate = Inquiry.objects.filter(
            email=p2p_email,
            created__gte=timezone.now() - timedelta(seconds=2)
        ).exists()

        if recent_duplicate:
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
        
        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
        
        else:
            return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })

    else:
        return render(request, 'basecamp/booking/p2p.html', {})
    

# p2p multiple points booking by myself 
def p2p_booking_detail(request):
    if request.method == "POST":
        token = request.POST.get('cf-turnstile-response', '')
        ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
        if not verify_turnstile(token, ip):
            return JsonResponse({'success': False, 'error': 'Security verification failed. Please try again.'})
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
        price = request.POST.get('price')

        subject = "Multiple points booking confirmation"
        template_name = "html_email-p2p-confirmation.html"

        context = {
            'p2p_name': p2p_name, 'p2p_phone': p2p_phone, 'p2p_email': p2p_email, 'p2p_date': p2p_date, 
            'first_pickup_location': first_pickup_location, 'first_putime': first_putime,  
            'second_pickup_location': second_pickup_location, 'second_putime': second_putime, 
            'third_pickup_location': third_pickup_location, 'third_putime': third_putime, 
            'fourth_pickup_location': fourth_pickup_location, 'fourth_putime': fourth_putime,
            'first_dropoff_location': first_dropoff_location, 
            'second_dropoff_location': second_dropoff_location, 
            'third_dropoff_location': third_dropoff_location,  
            'fourth_dropoff_location': fourth_dropoff_location, 
            'p2p_passengers': p2p_passengers, 'p2p_baggage': p2p_baggage, 'p2p_message': p2p_message,
            'price': price
        }

        handle_email_sending(request, p2p_email, subject, template_name, context)        
        
        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
        
        else:
            return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })

    else:
        return render(request, 'basecamp/booking/p2p.html', {})


def price_detail(request):
    sorted_suburbs = get_sorted_suburbs() 
    if request.method == "POST":
        pickup_date_str = request.POST.get('pickup_date', '')  
        start_point = request.POST.get('start_point')
        end_point = request.POST.get('end_point')
        no_of_passenger = request.POST.get('no_of_passenger')
        
        # 1. 'Select your option' 검증
        if start_point == 'Select your option' or end_point == 'Select your option':
            return render(request, 'basecamp/error/home_error.html')

        # 2. 픽업 날짜 유효성 검사 적용 
        try:
            pickup_date = parse_date(pickup_date_str, field_name="Pickup Date")

        except ValueError as e:
            suburbs = get_suburbs()
            home_suburbs = get_home_suburbs()
            return render(request, 'basecamp/home.html', {
                'error_message': str(e), 
                'suburbs': suburbs,
                'home_suburbs': home_suburbs,
                
                'start_point_value': start_point if start_point != 'Select your option' else '',
                'end_point_value': end_point if end_point != 'Select your option' else '',
                'no_of_passenger_value': no_of_passenger,
            })

        request.session['original_start_point'] = start_point
        request.session['original_end_point'] = end_point

        normalized_start_point = start_point
        normalized_end_point = end_point

        if start_point in ["Sydney Int'l Airport", "Sydney Domestic Airport"]:
            normalized_start_point = 'Airport'

        if end_point in ["Sydney Int'l Airport", "Sydney Domestic Airport"]:
            normalized_end_point = 'Airport'

        condition_met = not (
            (normalized_start_point in ['Overseas cruise terminal', 'WhiteBay cruise terminal'] and normalized_end_point == 'Airport') or
            (normalized_start_point == 'Airport' and normalized_end_point in ['Overseas cruise terminal', 'WhiteBay cruise terminal'])
        )

        context = {
            'pickup_date': pickup_date.strftime('%Y-%m-%d'), 
            'start_point': normalized_start_point,
            'end_point': normalized_end_point,
            'no_of_passenger': no_of_passenger,
            'condition_met': condition_met
        }

        return render(request, 'basecamp/booking/inquiry1.html', context)

    else:
        return render(request, 'basecamp/home.html', {
            'home_suburbs': sorted_suburbs,
        })
    

# Booking by myself 
def confirmation_detail(request):
    if request.method == "POST":
        pickup_date_str = request.POST.get('pickup_date', '')           
        return_pickup_date_str = request.POST.get('return_pickup_date', '')
        company_name = request.POST.get('company_name', '')
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        email1 = request.POST.get('email1', '')   
        flight_number = request.POST.get('flight_number', '')
        flight_time = request.POST.get('flight_time', '')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction', '')
        suburb = request.POST.get('suburb', '')
        street = request.POST.get('street', '')
        start_point = request.POST.get('start_point', '')
        end_point = request.POST.get('end_point', '')
        no_of_passenger = request.POST.get('no_of_passenger')
        return_direction = request.POST.get('return_direction')
        return_flight_number = request.POST.get('return_flight_number', '')
        return_flight_time = request.POST.get('return_flight_time', '')
        return_pickup_time = request.POST.get('return_pickup_time')
        return_start_point = request.POST.get('return_start_point', '')
        return_end_point = request.POST.get('return_end_point', '')
        message = request.POST.get('message', '') 
        notice = request.POST.get('notice', '')       
        price = request.POST.get('price', '')
        paid = request.POST.get('paid', '')
        cash = to_bool(request.POST.get('cash', ''))
        prepay = to_bool(request.POST.get('prepay', ''))  

        try:
            pickup_date_obj = parse_date(
                pickup_date_str, 
                field_name="Pickup Date", 
                required=True
            )

            return_pickup_date_obj = parse_date(
                return_pickup_date_str, 
                field_name="Return Pickup Date", 
                required=False, 
                reference_date=pickup_date_obj 
            )
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}) 

        data = {            
            'name': name,
            'contact': contact,
            'email': email,
            'pickup_date': pickup_date_obj.strftime('%Y-%m-%d'),
            'flight_number': flight_number,
            'pickup_time': pickup_time,
            'start_point': start_point,
            'street': street,
            'end_point': end_point,
            'no_of_passenger': no_of_passenger,
            'message': message,
        }    
        
        inquiry_email = Inquiry.objects.filter(email=email).exists()
        post_email = Post.objects.filter(email=email).exists()  

        email_content_template = '''
        Hello, {name} \n
        {status_message}\n 
        *** It starts from Home Page
        =============================
        Contact: {contact}
        Email: {email}  
        ✅ Pickup date: {pickup_date}
        Flight number: {flight_number}
        Pickup time: {pickup_time}
        start_point: {start_point}
        Street: {street}
        end_point: {end_point}
        Passenger: {no_of_passenger}
        Message: {message}
        =============================\n        
        Best Regards,
        EasyGo Admin \n\n        
        '''

        if inquiry_email or post_email:
            data['status_message'] = "✅ **Exist in Inquiry or Post ***"
            subject = f"[Confirmation] Existing Customer - {data['name']}"
        else:
            data['status_message'] = "*** Neither in Inquiry & Post ***"
            subject = f"[Confirmation] New Customer - {data['name']}"

        content = email_content_template.format(**data)

        send_mail(subject, content, '', [RECIPIENT_EMAIL])  

        sam_driver = Driver.objects.get(driver_name="Sam") 

        # 🧳 개별 수하물 항목 수집
        large = to_int(request.POST.get('baggage_large'))
        medium = to_int(request.POST.get('baggage_medium'))
        small = to_int(request.POST.get('baggage_small'))

        baby_seat = to_int(request.POST.get('baggage_baby'))
        booster_seat = to_int(request.POST.get('baggage_booster'))
        pram = to_int(request.POST.get('baggage_pram'))

        ski = to_int(request.POST.get('baggage_ski'))
        snowboard = to_int(request.POST.get('baggage_snowboard'))
        golf = to_int(request.POST.get('baggage_golf'))
        bike = to_int(request.POST.get('baggage_bike'))
        boxes = to_int(request.POST.get('baggage_boxes'))
        musical_instrument = to_int(request.POST.get('baggage_music'))

        # Oversize flags (수량 있을 때만 유효)
        ski_oversize = ski > 0 and request.POST.get('ski_oversize') == 'on'
        snowboard_oversize = snowboard > 0 and request.POST.get('snowboard_oversize') == 'on'
        golf_oversize = golf > 0 and request.POST.get('golf_oversize') == 'on'
        bike_oversize = bike > 0 and request.POST.get('bike_oversize') == 'on'
        boxes_oversize = boxes > 0 and request.POST.get('boxes_oversize') == 'on'
        musical_instrument_oversize = (
            musical_instrument > 0 and request.POST.get('music_oversize') == 'on'
        )

        # 🎯 요약 문자열 생성
        baggage_summary = []

        # Standard luggage
        add_bag(baggage_summary, "L", large)
        add_bag(baggage_summary, "M", medium)
        add_bag(baggage_summary, "S", small)

        # Seats / prams
        add_bag(baggage_summary, "Baby", baby_seat)
        add_bag(baggage_summary, "Booster", booster_seat)
        add_bag(baggage_summary, "Pram", pram)

        # Oversize-capable items
        add_bag(baggage_summary, "Ski", ski, ski_oversize)
        add_bag(baggage_summary, "Snow", snowboard, snowboard_oversize)
        add_bag(baggage_summary, "Golf", golf, golf_oversize)
        add_bag(baggage_summary, "Bike", bike, bike_oversize)
        add_bag(baggage_summary, "Box", boxes, boxes_oversize)
        add_bag(baggage_summary, "Music", musical_instrument, musical_instrument_oversize)

        baggage_str = ", ".join(baggage_summary)

        p = Post(company_name=company_name, name=name, contact=contact, email=email, email1=email1, pickup_date=pickup_date_obj, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, start_point=start_point, end_point=end_point, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=baggage_str, message=message, return_direction=return_direction, return_pickup_date=return_pickup_date_obj, 
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, return_pickup_time=return_pickup_time, return_start_point=return_start_point,
                 return_end_point=return_end_point, notice=notice, price=price, paid=paid, cash=cash, prepay=prepay, driver=sam_driver)
        
        p.save()        

        rendering = render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })
        
        return rendering

    else:
        return render(request, 'basecamp/booking/confirmation.html', {})


# airport booking by client
def booking_detail(request):
    if request.method == "POST":
        token = request.POST.get('cf-turnstile-response', '')
        ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
        if not verify_turnstile(token, ip):
            return JsonResponse({'success': False, 'error': 'Security verification failed. Please try again.'})
        pickup_date_str = request.POST.get('pickup_date', '')
        return_pickup_date_str = request.POST.get('return_pickup_date', '')
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        flight_number = request.POST.get('flight_number', '')
        flight_time = request.POST.get('flight_time', '')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')      
        suburb = request.POST.get('suburb')
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
            pickup_date_obj = parse_date(
                pickup_date_str, 
                field_name="Pickup Date", 
                required=True
            )

            return_pickup_date_obj = parse_date(
                return_pickup_date_str, 
                field_name="Return Pickup Date", 
                required=False, 
                reference_date=pickup_date_obj 
            )
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        price = 'TBA'

        # turnstile_response = request.POST.get('cf-turnstile-response')
        # if not verify_turnstile(turnstile_response, remoteip=request.META.get('REMOTE_ADDR')):
        #     return JsonResponse({'success': False, 'error': 'Turnstile verification failed. Please try again.'})

        # ✅ 중복 제출 방지
        recent_duplicate = Post.objects.filter(
            email=email,
            created__gte=timezone.now() - timedelta(seconds=2)
        ).exists()

        if recent_duplicate:
            return JsonResponse({'success': False, 'message': 'Duplicate form recently submitted. Please wait before trying again.'})  
        
        data = {
            'name': name,
            'contact': contact,
            'email': email,            
            'pickup_date': pickup_date_obj.strftime('%Y-%m-%d'),
            'pickup_time': pickup_time,
            'flight_number': flight_number,            
            'street': street, 
            'suburb': suburb,
            'no_of_passenger': no_of_passenger,
            'return_pickup_date': return_pickup_date_obj.strftime('%Y-%m-%d') if return_pickup_date_obj else '',
            'return_flight_number': return_flight_number,
            'return_flight_time': return_flight_time,
            'return_pickup_time': return_pickup_time,
        }

        inquiry_email = Inquiry.objects.filter(email=email).exists()
        post_email = Post.objects.filter(email=email).exists()  

        # 1. 템플릿 정의 (키워드 기반 포맷팅)
        email_content_template = '''
        Hello, {name} \n  
        [Booking by client] >> Sending email only!\n
        {status_message}\n            
        ===============================
        Contact: {contact}
        Email: {email}  
        ✅ Pickup date: {pickup_date}
        Pickup time: {pickup_time}
        Flight number: {flight_number}
        Address: {street}, {suburb}
        No of Pax: {no_of_passenger}
        ✅ Return pickup date: {return_pickup_date}
        Return flight no: {return_flight_number}
        Return flight time: {return_flight_time}    
        Return pickup time: {return_pickup_time}   
        ===============================\n        
        Best Regards,
        EasyGo Admin \n\n        
        '''

        if inquiry_email or post_email:
            data['status_message'] = "Exist in Inquiry or Post *"
            subject = f"[Client Booking] Existing Customer - {data['name']}"
        else:
            data['status_message'] = "Neither in Inquiry & Post *"
            subject = f"[Client Booking] New Customer - {data['name']}"

        content = email_content_template.format(**data)

        send_mail(subject, content, '', [RECIPIENT_EMAIL])
            
        sam_driver = Driver.objects.get(driver_name="Sam") 

        # 🧳 개별 수하물 항목 수집
        large = to_int(request.POST.get('baggage_large'))
        medium = to_int(request.POST.get('baggage_medium'))
        small = to_int(request.POST.get('baggage_small'))

        baby_seat = to_int(request.POST.get('baggage_baby'))
        booster_seat = to_int(request.POST.get('baggage_booster'))
        pram = to_int(request.POST.get('baggage_pram'))

        ski = to_int(request.POST.get('baggage_ski'))
        snowboard = to_int(request.POST.get('baggage_snowboard'))
        golf = to_int(request.POST.get('baggage_golf'))
        bike = to_int(request.POST.get('baggage_bike'))
        boxes = to_int(request.POST.get('baggage_boxes'))
        musical_instrument = to_int(request.POST.get('baggage_music'))

        # Oversize flags (수량 있을 때만 유효)
        ski_oversize = ski > 0 and request.POST.get('ski_oversize') == 'on'
        snowboard_oversize = snowboard > 0 and request.POST.get('snowboard_oversize') == 'on'
        golf_oversize = golf > 0 and request.POST.get('golf_oversize') == 'on'
        bike_oversize = bike > 0 and request.POST.get('bike_oversize') == 'on'
        boxes_oversize = boxes > 0 and request.POST.get('boxes_oversize') == 'on'
        musical_instrument_oversize = (
            musical_instrument > 0 and request.POST.get('music_oversize') == 'on'
        )

        # 🎯 요약 문자열 생성
        baggage_summary = []

        # Standard luggage
        add_bag(baggage_summary, "L", large)
        add_bag(baggage_summary, "M", medium)
        add_bag(baggage_summary, "S", small)

        # Seats / prams
        add_bag(baggage_summary, "Baby", baby_seat)
        add_bag(baggage_summary, "Booster", booster_seat)
        add_bag(baggage_summary, "Pram", pram)

        # Oversize-capable items
        add_bag(baggage_summary, "Ski", ski, ski_oversize)
        add_bag(baggage_summary, "Snow", snowboard, snowboard_oversize)
        add_bag(baggage_summary, "Golf", golf, golf_oversize)
        add_bag(baggage_summary, "Bike", bike, bike_oversize)
        add_bag(baggage_summary, "Box", boxes, boxes_oversize)
        add_bag(baggage_summary, "Music", musical_instrument, musical_instrument_oversize)

        baggage_str = ", ".join(baggage_summary)

        p = Post(name=name, contact=contact, email=email, pickup_date=pickup_date_obj, flight_number=flight_number, flight_time=flight_time, 
                 pickup_time=pickup_time, start_point=start_point, end_point=end_point, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=baggage_str, message=message, return_direction=return_direction, 
                 return_pickup_date=return_pickup_date_obj, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, return_start_point=return_start_point, return_end_point=return_end_point, driver=sam_driver,
                 price=price, )
        
        p.save()        
        
        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
        
        else:
            return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })

    else:
        return render(request, 'basecamp/booking/booking.html', {})
    

# cruise booking by client
def cruise_booking_detail(request):
    if request.method == "POST":
        token = request.POST.get('cf-turnstile-response', '')
        ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
        if not verify_turnstile(token, ip):
            return JsonResponse({'success': False, 'error': 'Security verification failed. Please try again.'})
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
        recent_duplicate = Post.objects.filter(
            email=email,
            created__gte=timezone.now() - timedelta(seconds=2)
        ).exists()

        if recent_duplicate:
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'}) 

        try:
            pickup_date_obj = parse_date(
                pickup_date_str, 
                field_name="Pickup Date", 
                required=True
            )

            return_pickup_date_obj = parse_date(
                return_pickup_date_str, 
                field_name="Return Pickup Date", 
                required=False, 
                reference_date=pickup_date_obj 
            )
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})   
        
        data = {
            'name': name,
            'contact': contact, 
            'email': email,
            'pickup_date': pickup_date_obj.strftime('%Y-%m-%d'),
            'pickup_time': pickup_time,
            'start_point': start_point,
            'end_point': end_point,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'return_pickup_date': return_pickup_date_obj.strftime('%Y-%m-%d') if return_pickup_date_obj else '',
            'return_pickup_time': return_pickup_time, 
            'return_start_point': return_start_point,
            'message': message}       
        
        cruise_email = Inquiry.objects.filter(email=email).exists()
        post_email = Post.objects.filter(email=email).exists()  

        if cruise_email or post_email:             
                        
            content = '''
            Hello, {} \n  
            [Cruise Booking by client] >> Put price & Send email\n
     
            ===============================
            Email: {}  
            Contact: {}
            Pick up time: {}      
            Start point: {}            
            End point: {}  
            No of passenger: {}
            no_of_baggage: {}
            ✅ return_pickup_date: {}
            return_start_point: {}
            Return pickup time: {}     
            Message: {}     

            =============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['email'], data['contact'], data['pickup_time'], data['start_point'], data['end_point'], 
                        data['no_of_passenger'], data['no_of_baggage'], data['return_pickup_date'], data['return_start_point'],
                        data['return_pickup_time'], data['message'])
            send_mail(data['pickup_date'], content, '', [RECIPIENT_EMAIL])
        
        else:
            content = '''
            Hello, {} \n  
            [Cruise Booking by client] >> Put price & Send email \n

           ===============================
            Email: {}  
            Contact: {}
            Pick up time: {}      
            Start point: {}            
            End point: {}  
            No of passenger: {}
            no_of_baggage: {}
            ✅return_pickup_date: {}
            return_flight_number: {}
            Return pickup time: {}     
            Message: {}     
            
            =============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['email'], data['contact'], data['pickup_time'], data['start_point'], data['end_point'], 
                        data['no_of_passenger'], data['no_of_baggage'], data['return_pickup_date'], data['return_start_point'],
                        data['return_pickup_time'], data['message'])
            send_mail(data['pickup_date'], content, '', [RECIPIENT_EMAIL])
            
        sam_driver = Driver.objects.get(driver_name="Sam")

        # 🧳 개별 수하물 항목 수집
        large = to_int(request.POST.get('baggage_large'))
        medium = to_int(request.POST.get('baggage_medium'))
        small = to_int(request.POST.get('baggage_small'))

        baby_seat = to_int(request.POST.get('baggage_baby'))
        booster_seat = to_int(request.POST.get('baggage_booster'))
        pram = to_int(request.POST.get('baggage_pram'))

        ski = to_int(request.POST.get('baggage_ski'))
        snowboard = to_int(request.POST.get('baggage_snowboard'))
        golf = to_int(request.POST.get('baggage_golf'))
        bike = to_int(request.POST.get('baggage_bike'))
        boxes = to_int(request.POST.get('baggage_boxes'))
        musical_instrument = to_int(request.POST.get('baggage_music'))

        # Oversize flags (수량 있을 때만 유효)
        ski_oversize = ski > 0 and request.POST.get('ski_oversize') == 'on'
        snowboard_oversize = snowboard > 0 and request.POST.get('snowboard_oversize') == 'on'
        golf_oversize = golf > 0 and request.POST.get('golf_oversize') == 'on'
        bike_oversize = bike > 0 and request.POST.get('bike_oversize') == 'on'
        boxes_oversize = boxes > 0 and request.POST.get('boxes_oversize') == 'on'
        musical_instrument_oversize = (
            musical_instrument > 0 and request.POST.get('music_oversize') == 'on'
        )

        # 🎯 요약 문자열 생성
        baggage_summary = []

        # Standard luggage
        add_bag(baggage_summary, "L", large)
        add_bag(baggage_summary, "M", medium)
        add_bag(baggage_summary, "S", small)

        # Seats / prams
        add_bag(baggage_summary, "Baby", baby_seat)
        add_bag(baggage_summary, "Booster", booster_seat)
        add_bag(baggage_summary, "Pram", pram)

        # Oversize-capable items
        add_bag(baggage_summary, "Ski", ski, ski_oversize)
        add_bag(baggage_summary, "Snow", snowboard, snowboard_oversize)
        add_bag(baggage_summary, "Golf", golf, golf_oversize)
        add_bag(baggage_summary, "Bike", bike, bike_oversize)
        add_bag(baggage_summary, "Box", boxes, boxes_oversize)
        add_bag(baggage_summary, "Music", musical_instrument, musical_instrument_oversize)

        baggage_str = ", ".join(baggage_summary)                    

        p = Post(name=name, contact=contact, email=email, pickup_date=pickup_date_obj, start_point=start_point,
                 end_point=end_point, pickup_time=pickup_time, price=price,
                 no_of_passenger=no_of_passenger, no_of_baggage=baggage_str,   
                 return_pickup_date=return_pickup_date_obj, return_start_point=return_start_point,  
                 return_pickup_time=return_pickup_time, return_end_point=return_end_point,
                 message=message, driver=sam_driver, )
        
        p.save()

        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
        
        else:
            return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })

    else:
        return render(request, 'basecamp/booking/cruise_booking.html', {})


def confirm_booking_detail(request):
    if request.method == "POST":
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

        users = Inquiry.objects.filter(email__iexact=email)
        if users.exists() and 0 <= index < len(users):
            user = users[index]
        else:
            return render(request, 'basecamp/email/email_error_confirmbooking.html')

        # 기존 데이터
        name = user.name
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
        paid = user.paid
        private_ride = user.private_ride

        try:
            pickup_date_obj = parse_date(pickup_date, field_name="Pickup Date", required=True)
            return_pickup_date_obj = parse_date(
                return_pickup_date, field_name="Return Pickup Date", required=False, reference_date=pickup_date
            )
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        # 최종 가격 계산
        if price in [None, ""]:
            final_price = "TBA"
            toll_value = ""
        else:
            try:
                final_price = float(price) + float(toll)
                toll_value = "toll included" if toll else ""
            except Exception:
                final_price = price
                toll_value = "toll included" if toll else ""

        # pending 상태 결정
        if paid or cash:
            pending = False
        elif prepay:
            pending = True
        else:
            pending = True  

        # 이메일 발송용 데이터
        data = {
            'name': name,
            'email': email,
            'contact': contact,
            'company_name': company_name,
            'pickup_date': pickup_date.strftime('%Y-%m-%d'),
            'pickup_time': pickup_time,
            'direction': direction,
            'flight_number': flight_number,
            'flight_time': flight_time,
            'cash': cash,
            'prepay': prepay,
            'return_flight_number': return_flight_number,
            'street': street,
            'suburb': suburb,
            'start_point': start_point,
            'end_point': end_point,
            'return_start_point': return_start_point,
            'return_end_point': return_end_point
        }

        send_confirm_email.delay(
            data['name'], data['email'], data['contact'], data['company_name'],
            data['direction'], data['flight_number'], data['flight_time'],
            data['pickup_date'], data['pickup_time'], data['return_flight_number'],
            data['street'], data['suburb'], data['start_point'], data['end_point'],
            data['cash'], data['prepay'], data['return_start_point'], data['return_end_point']
        )

        sam_driver = Driver.objects.get(driver_name="Sam")
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
            message=message, notice=notice,
            price=final_price, toll=toll_value, prepay=prepay, pending=pending,
            paid=paid, cash=cash, is_confirmed=is_confirmed, driver=sam_driver
        )

        p.save()
        
        user.delete()

        return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })

    else:
        return render(request, 'basecamp/booking/confirm_booking.html', {})

     
# sending confirmation email first one   
def sending_email_first_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        prepay_raw = request.POST.get('prepay')  # May be None
        cash_raw = request.POST.get('cash')  # May be None
        index = request.POST.get('index', '1')

        try:
            index = int(index) - 1  
        except ValueError:
            return HttpResponse("Invalid index value", status=400)  
        
        users = Post.objects.filter(email__iexact=email)        
        if users.exists() and 0 <= index < len(users):
            user = users[index]  

            # price 처리
            if user.price in [None, ""]:
                display_price = "TBA"
            else:
                display_price = user.price

            form_prepay = (prepay_raw == 'True') if prepay_raw is not None else False
            final_prepay = bool(user.prepay) or form_prepay            

            form_cash = (cash_raw == 'True') if cash_raw is not None else False
            final_cash = bool(user.cash) or form_cash

            user.prepay = final_prepay
            user.cash = final_cash  
            user.price = display_price
            user.sent_email = True
            user.save()
            
            if user.cancelled: 
                template_name = "html_email-cancelled.html"
                subject = "Booking Cancellation Notice - EasyGo" 
                
                context = {
                    'name': user.name, 
                    'email': user.email,
                    'pickup_date': user.pickup_date or "",
                    'pickup_time': user.pickup_time or "",
                    'return_pickup_date': user.return_pickup_date or "",
                    'return_pickup_time': user.return_pickup_time or "", 
                        }

                handle_email_sending(request, user.email, subject, template_name, context)
                    
            else: 
                template_name = "html_email-confirmation.html"

                html_content = render_email_template(
                                        "html_email-confirmation.html", 
                                        {
                                            'company_name': user.company_name, 'name': user.name, 'contact': user.contact, 'email': user.email, 'email1': user.email1,
                                            'pickup_date': user.pickup_date, 'flight_number': user.flight_number,
                                            'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                            'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                            'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                            'return_direction': user.return_direction, 'return_pickup_date': user.return_pickup_date, 
                                            'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                                            'return_pickup_time': user.return_pickup_time,'message': user.message, 'notice': user.notice, 
                                            'price': display_price, 'paid': user.paid, 'cash': final_cash, 'prepay': final_prepay,
                                            'toll': getattr(user, 'toll', 0), 'start_point': getattr(user, 'start_point', ''), 
                                            'end_point': getattr(user, 'end_point', ''), 'return_start_point': getattr(user, 'return_start_point', ''), 
                                            'return_end_point': getattr(user, 'return_end_point', ''), 
                                        })

                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives(
                    "Booking confirmation - EasyGo",
                    text_content,
                    '',
                    [email, RECIPIENT_EMAIL]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

            return render(request, 'basecamp/inquiry_done.html', {
                'google_review_url': settings.GOOGLE_REVIEW_URL,            
            })  
        
        else:            
            return HttpResponse("No user found", status=400)

    else:
        return render(request, 'basecamp/email/sending_email_first.html', {})
    

# sending confirmation email second one    
def sending_email_second_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        prepay_raw = request.POST.get('prepay')  # May be None
        cash_raw = request.POST.get('cash')  # May be None

        user = Post.objects.filter(email__iexact=email)[1]
        user1 = Post.objects.filter(email__iexact=email).first() 

        # prepay / cash 처리
        form_prepay = (prepay_raw == 'True') if prepay_raw is not None else False
        final_prepay = bool(user.prepay) or bool(user1.prepay) or form_prepay            

        form_cash = (cash_raw == 'True') if cash_raw is not None else False
        final_cash = bool(user.cash) or bool(user1.cash) or form_cash

        user.prepay = final_prepay
        user.cash = final_cash 
        user.sent_email = True

        user1.prepay = final_prepay
        user1.cash = final_cash
        user1.sent_email = True

        # price 안전 처리 및 DB에 저장
        if user.price in [None, ""]:
            user.price = "TBA"
        if user1.price in [None, ""]:
            user1.price = "TBA"

        user.save()
        user1.save()

        # price 계산 (숫자가 아니면 0으로 처리)
        price1 = float(user.price) if isinstance(user.price, (int, float, str)) and str(user.price).replace('.', '', 1).isdigit() else 0
        price2 = float(user1.price) if isinstance(user1.price, (int, float, str)) and str(user1.price).replace('.', '', 1).isdigit() else 0
        double_price = price1 + price2

        # paid 계산
        paid1 = float(user.paid) if user.paid else 0
        paid2 = float(user1.paid) if user1.paid else 0
        double_paid = paid1 + paid2

        if user.cancelled or user1.cancelled:
            template_name = "html_email-cancelled.html"
            subject = "Booking Cancellation Notice - EasyGo" 
            
            context = {
                'name': user.name, 
                'email': user.email,
                'pickup_date': user.pickup_date or "",
                'pickup_time': user.pickup_time or "",
                'return_pickup_date': user.return_pickup_date or "",
                'return_pickup_time': user.return_pickup_time or "", 
            }

            handle_email_sending(request, user.email, subject, template_name, context)

        else:
            template_name = "html_email-confirmation.html"
            subject = "Booking confirmation - EasyGo"

            context = { 
                'company_name': user.company_name, 
                'name': user.name, 
                'contact': user.contact, 
                'email': user.email, 
                'email1': user.email1,
                'pickup_date': user.pickup_date, 
                'flight_number': user.flight_number,
                'flight_time': user.flight_time, 
                'pickup_time': user.pickup_time,
                'direction': user.direction, 
                'street': user.street, 
                'suburb': user.suburb, 
                'start_point': getattr(user, 'start_point', ''),
                'no_of_passenger': user.no_of_passenger, 
                'no_of_baggage': user.no_of_baggage, 
                'end_point': getattr(user, 'end_point', ''),
                'return_direction': user.return_direction, 
                'return_pickup_date': user.return_pickup_date, 
                'return_flight_number': user.return_flight_number, 
                'return_flight_time': user.return_flight_time, 
                'return_pickup_time': user.return_pickup_time, 
                'message': user.message, 
                'notice': user.notice, 
                'price': f"{user.price} + {user1.price}" if "TBA" in [user.price, user1.price] else double_price,
                'paid': double_paid, 
                'cash': user.cash, 
                'prepay': user.prepay,
                'toll': getattr(user, 'toll', 0), 
                'return_start_point': getattr(user, 'return_start_point', ''), 
                'return_end_point': getattr(user, 'return_end_point', ''), 
            }

            html_content = render_email_template(template_name, context)
            text_content = strip_tags(html_content)

            recipient_list = [user.email, RECIPIENT_EMAIL]
            if user.email1:
                recipient_list.append(user.email1)

            email_message = EmailMultiAlternatives(
                subject,
                text_content,
                '',
                recipient_list,
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()
            
        return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        }) 
    
    else:
        return render(request, 'basecamp/email/sending_email_second.html', {})
    

def sending_email_input_data_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')   
        field = request.POST.get('field')        

        inquiry = Inquiry.objects.filter(email__iexact=email).first()
        post = Post.objects.filter(email__iexact=email).first()

        user = None
        for obj in [inquiry, post]:
            if obj:
                if user is None or obj.created > user.created:
                    user = obj

        if not user:
            return render(request, 'basecamp/400.html')

        else:
            template_name = "html_email-input-date.html"
            subject = "Checking details - EasyGo"

            # 템플릿에 전달할 컨텍스트 구성
            context = {
                'name': user.name, 'contact': user.contact, 'email': user.email, 
                'pickup_date': user.pickup_date, 'flight_number': user.flight_number,
                'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                'no_of_baggage': user.no_of_baggage, 'field': field, 
                'start_point': user.start_point, 'end_point': user.end_point,
                'return_start_point': user.return_start_point, 'return_end_point': user.return_end_point,
                'return_direction': user.return_direction, 'return_pickup_date': user.return_pickup_date, 
                'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                'return_pickup_time': user.return_pickup_time,'message': user.message, 'notice': user.notice, 
            }

            handle_email_sending(request, user.email, subject, template_name, context)

        return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })
    
    else:
        return render(request, 'basecamp/email/sending_email_first.html', {})   


# For Return Trip 
def return_trip_detail(request):
    if request.method == "POST":
        token = request.POST.get('cf-turnstile-response', '')
        ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
        if not verify_turnstile(token, ip):
            return JsonResponse({'success': False, 'error': 'Security verification failed. Please try again.'})
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
        price = request.POST.get('price', '')
        toll = request.POST.get('toll', '')
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
            return render(request, 'basecamp/403.html')    
            
        else:
            name = user.name     
            company_name = user.company_name       
            contact = user.contact
            suburb = user.suburb
            street = user.street
            no_of_passenger = user.no_of_passenger
            no_of_baggage = user.no_of_baggage            
            if not start_point:
                start_point = user.start_point
            if not end_point:
                end_point = user.end_point

            # 날짜 파싱 
            try:
                pickup_date_obj = parse_date(
                    pickup_date_str, 
                    field_name="Pickup Date", 
                    required=True
                )

                return_pickup_date_obj = parse_date(
                    return_pickup_date_str, 
                    field_name="Return Pickup Date", 
                    required=False, 
                    reference_date=pickup_date_obj 
                )
            except ValueError as e:
                return JsonResponse({'success': False, 'error': str(e)})

        # ✅ 중복 제출 방지 
        recent_duplicate = Post.objects.filter(
            email=email,
            created__gte=timezone.now() - timedelta(seconds=2)
        ).exists()

        if recent_duplicate:
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})             
            
        data = {
            'name': name,
            'contact': contact,
            'email': email,
            }       
            
        content_template = '''
        {name} 
        ✅ submitted the 'Return trip' \n

        https://easygoshuttle.com.au/sending_email_first/ \n  
        https://easygoshuttle.com.au/sending_email_second/ \n
        ===============================
        Contact: {contact}
        Email: {email}  
        ===============================\n        
        Best Regards,
        EasyGo Admin \n\n        
        '''
        content = content_template.format(**data)

        subject = f"[New Return Trip] Submission from {data['name']})"

        send_mail(subject, content, '', [RECIPIENT_EMAIL])
         
        sam_driver = Driver.objects.get(driver_name="Sam")  
                    
        p = Post(name=name, company_name=company_name, contact=contact, email=email, pickup_date=pickup_date_obj, flight_number=flight_number, flight_time=flight_time, 
                 pickup_time=pickup_time, start_point=start_point, end_point=end_point, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, cash=cash, prepay=prepay, return_direction=return_direction, 
                 return_pickup_date=return_pickup_date_obj, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, return_start_point=return_start_point, return_end_point=return_end_point, driver=sam_driver,
                 price=price, toll=toll)
        
        p.save()

        rendering = render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })   
        
        return rendering
    
    else:
        return render(request, 'basecamp/booking/return_trip.html', {})  


def invoice_detail(request):
    if request.method == "POST":
        token = request.POST.get('cf-turnstile-response', '')
        ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
        if not verify_turnstile(token, ip):
            return JsonResponse({'success': False, 'error': 'Security verification failed. Please try again.'})
        email = request.POST.get('email', '').strip()
        extra_email = request.POST.get('extra_email', '').strip()
        apply_gst_flag = request.POST.get('apply_gst')
        surcharge_input = request.POST.get('surcharge')
        discount_input = request.POST.get('discount')
        inv_no = request.POST.get('inv_no')
        toll_input = request.POST.get('toll')
        index = request.POST.get('index', '1')
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')

        try:
            index = int(index) - 1
        except ValueError:
            return HttpResponse("Invalid index value", status=400)

        users = Post.objects.filter(email__iexact=email)
        if not users.exists():
            return HttpResponse("No bookings found", status=404)
        else:
            user = users[0]
            today = date.today()
            # ✅ Use provided inv_no if exists, else use old logic
            if inv_no and inv_no.strip():
                inv_no = inv_no.strip()
            else:
                inv_no = f"{user.pickup_date.toordinal()}" if user.pickup_date else "896021"

        DEFAULT_BANK = getattr(settings, "DEFAULT_BANK_CODE", "westpac")

        # Multi booking 여부
        multiple = False
        if from_date and to_date:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            bookings = users.filter(pickup_date__range=(from_date_obj, to_date_obj)).order_by('pickup_date', 'pickup_time')
            multiple = True
            if not bookings.exists():
                return HttpResponse(
                    "No bookings found in selected date range",
                    status=404
                )
        else:
            bookings = [users[index]] if 0 <= index < len(users) else [users.first()]

        if multiple:
            for booking in bookings:
                if booking.company_name and not booking.prepay:
                    if not user.cash:  # 🚨 cash인 경우는 제외
                        booking.price = round(float(booking.price) * 1.10, 2)
                        booking.prepay = True
                        booking.save()

            booking_data = []
            total_price_without_gst = total_paid = grand_total = 0
            total_gst = total_surcharge = total_toll = 0

            for booking in bookings:
                if booking.start_point:
                    start_point = booking.start_point
                    end_point = booking.end_point
                    # 리턴 구간 존재 시 덮어쓰기 또는 별도 처리
                    if getattr(booking, 'return_start_point', None):
                        return_start_point = booking.return_start_point
                        return_end_point = booking.return_end_point
                    else:
                        return_start_point = None
                        return_end_point = None
                else:
                    direction = booking.direction or ""
                    if "Drop off to Domestic" in direction:
                        start_point = f"{booking.street}, {booking.suburb}"
                        end_point = "Domestic Airport"
                    elif "Drop off to Intl" in direction:
                        start_point = f"{booking.street}, {booking.suburb}"
                        end_point = "International Airport"
                    elif "Pickup from Domestic" in direction:
                        start_point = "Domestic Airport"
                        end_point = f"{booking.street}, {booking.suburb}"
                    elif "Pickup from Intl" in direction:
                        start_point = "International Airport"
                        end_point = f"{booking.street}, {booking.suburb}"
                    else:
                        start_point = "Unknown"
                        end_point = "Unknown"

                price = safe_float(booking.price) or 0.0
                with_gst = round(price * 0.10, 2) if apply_gst_flag else 0.0

                # ✅ Surcharge handling
                if surcharge_input == "Yes":
                    surcharge_calc = round(price * 0.03, 2)
                    surcharge_display = surcharge_calc
                elif surcharge_input:
                    surcharge_calc = 0.0
                    surcharge_display = surcharge_input
                else:
                    surcharge_calc = 0.0
                    surcharge_display = 0.0

                toll = safe_float(toll_input) if toll_input else safe_float(booking.toll) or 0.0
                paid = safe_float(booking.paid) or 0.0
                total = price + with_gst + surcharge_calc + toll

                total_price_without_gst += price
                total_gst += with_gst
                total_surcharge += surcharge_calc
                total_toll += toll
                total_paid += paid
                grand_total += total

                paid = safe_float(booking.paid) or 0.0

                booking_data.append({
                    "pickup_date": booking.pickup_date,
                    "pickup_time": booking.pickup_time,
                    "start_point": start_point,
                    "end_point": end_point,
                    "no_of_passenger": booking.no_of_passenger,
                    "no_of_baggage": booking.no_of_baggage,
                    "message": booking.message,
                    "notice": booking.notice,
                    "price": price,
                    "with_gst": with_gst,
                    "surcharge": surcharge_display,
                    "toll": toll,
                    "total_price": total,
                })

            first_booking = bookings.first() if hasattr(bookings, "first") else (bookings[0] if bookings else None)

            if (discount_input or '') == 'Yes':
                discount = 0.0
            elif (discount_input or '').replace('.', '', 1).isdigit():
                discount = float(discount_input)
            elif first_booking and (first_booking.discount or '').replace('.', '', 1).isdigit():
                discount = float(first_booking.discount)
            else:
                discount = 0.0

            final_total = grand_total - discount
            total_balance = round(final_total - total_paid, 2)

            DEFAULT_BANK = getattr(settings, "DEFAULT_BANK_CODE", "westpac")

            first_booking = bookings[0] if bookings else None

            context = {
                "inv_no": inv_no,
                "company_name": first_booking.company_name if first_booking else "",
                "name": first_booking.name if first_booking else "",
                "apply_gst_flag": bool(apply_gst_flag),
                "invoice_date": today,
                "bookings": booking_data,
                "total_price_without_gst": round(total_price_without_gst, 2),
                "with_gst": round(total_gst, 2),
                "surcharge": round(total_surcharge, 2),
                "toll": round(total_toll, 2),
                "discount": discount,
                "total_price": round(final_total, 2),
                "paid": round(total_paid, 2),
                "balance": round(total_balance, 2),
                "DEFAULT_BANK": DEFAULT_BANK,
            }

            template_name = "html_email-multi-invoice.html"
            html_content = render_email_template(template_name, context)

        else:
            user = bookings[0]
            if not user:
                return HttpResponse("No booking found", status=404)

            start_point = user.start_point
            end_point = user.end_point

            price = safe_float(user.price) or 0.0
            with_gst = round(price * 0.10, 2) if user.company_name else 0.0

            # Surcharge handling
            if surcharge_input == "Yes":
                surcharge_calc = round(price * 0.03, 2)
                surcharge_display = surcharge_calc
            elif surcharge_input:
                surcharge_calc = 0.0
                surcharge_display = surcharge_input
            else:
                surcharge_calc = 0.0
                surcharge_display = 0.0

            toll = safe_float(toll_input) if toll_input else safe_float(user.toll) or 0.0

            if (discount_input or '') == 'Yes':
                discount = 0.0
            elif (discount_input or '').replace('.', '', 1).isdigit():
                discount = float(discount_input)
            elif (user.discount or '').replace('.', '', 1).isdigit():
                discount = float(user.discount)
            else:
                discount = 0.0

            total_price = price + with_gst + surcharge_calc + toll - discount
            float_paid = safe_float(user.paid) or 0.0
            balance = round(total_price - float_paid, 2)

            if user.cash and user.paid:
                cash_balance = balance - (with_gst + surcharge_calc)
                template_name = "html_email-invoice-cash.html"
                context = {
                    "inv_no": inv_no, "name": user.name, "company_name": user.company_name,
                    "apply_gst_flag": bool(apply_gst_flag),
                    "contact": user.contact, "discount": discount, "email": email,
                    "pickup_date": user.pickup_date, "pickup_time": user.pickup_time,    
                    "start_point": start_point, "end_point": end_point, "invoice_date": today,
                    "price": user.price, "with_gst": with_gst, "surcharge": surcharge_display,
                    "total_price": total_price, "toll": toll, "balance": cash_balance, 
                    "paid": float_paid, "message": user.message, "no_of_passenger": user.no_of_passenger,
                    "no_of_baggage": user.no_of_baggage, "notice": user.notice, "street": user.street, "suburb": user.suburb,
                    "return_pickup_time": user.return_pickup_time, "return_pickup_date": user.return_pickup_date, "DEFAULT_BANK": DEFAULT_BANK, 
                }

            elif user.return_pickup_time == "x":
                user1 = Post.objects.filter(email__iexact=email)[1]

                # 두 배 가격 계산
                base_price = safe_float(user1.price) or 0.0
                base_paid = safe_float(user1.paid) or 0.0

                doubled_price = base_price * 2
                doubled_paid = base_paid * 2  
                doubled_with_gst = round(doubled_price * 0.10, 2) if user1.company_name else 0.0
                doubled_surcharge = round(doubled_price * 0.03, 2) if surcharge_input else 0.0
                doubled_total = doubled_price + doubled_with_gst + doubled_surcharge + toll - discount
                balance = round(doubled_total - doubled_paid, 2)

                template_name = "html_email-invoice.html"
                context = {
                    "inv_no": inv_no, "name": user1.name, "company_name": user1.company_name,
                    "apply_gst_flag": bool(apply_gst_flag),
                    "contact": user1.contact, "pickup_date": user1.pickup_date, "pickup_time": user1.pickup_time,   
                    "start_point": user1.start_point, "end_point": user1.end_point, "invoice_date": today,
                    "price": doubled_price, "with_gst": doubled_with_gst, "surcharge": doubled_surcharge,
                    "total_price": doubled_total, "toll": toll, "balance": balance, "discount": discount,
                    "paid": doubled_paid, "message": user1.message, "no_of_passenger": user1.no_of_passenger,
                    "no_of_baggage": user1.no_of_baggage, "notice": user1.notice, "street": user1.street, "suburb": user1.suburb,
                    "return_pickup_time": user1.return_pickup_time, "return_pickup_date": user1.return_pickup_date, "DEFAULT_BANK": DEFAULT_BANK, 
                }
            else:
                template_name = "html_email-invoice.html"
                context = {
                    "inv_no": inv_no, "name": user.name, "company_name": user.company_name,
                    "apply_gst_flag": bool(apply_gst_flag),
                    "contact": user.contact, "pickup_date": user.pickup_date, "pickup_time": user.pickup_time,  
                    "start_point": start_point, "end_point": end_point, "invoice_date": today,
                    "price": user.price, "with_gst": with_gst, "surcharge": surcharge_display,
                    "total_price": total_price, "toll": toll, "balance": balance, "discount": discount,
                    "paid": float_paid, "message": user.message, "no_of_passenger": user.no_of_passenger,
                    "no_of_baggage": user.no_of_baggage, "notice": user.notice, "street": user.street, "suburb": user.suburb,
                    "return_pickup_time": user.return_pickup_time, "return_pickup_date": user.return_pickup_date, "DEFAULT_BANK": DEFAULT_BANK, 
                }

            html_content = render_email_template(template_name, context)

        text_content = strip_tags(html_content)
        recipient_list = [email, RECIPIENT_EMAIL]
        if extra_email:                
            recipient_list.append(extra_email)

        mail = EmailMultiAlternatives(
            f"Tax Invoice #T{inv_no} - EasyGo",
            text_content,
            DEFAULT_FROM_EMAIL,
            recipient_list
        )
        mail.attach_alternative(html_content, "text/html")

        # PDF 생성 및 첨부
        pdf = render_to_pdf(template_name, context)
        if pdf:
            mail.attach(f"Tax-Invoice-T{inv_no}.pdf", pdf, 'application/pdf')

        mail.send()

        if not multiple and user.company_name and not user.prepay:
            if not user.cash:  
                user.price = round(float(user.price) * 1.10, 2)
                user.prepay = True
                user.save()

        return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,            
        })

    else:
        return render(request, 'basecamp/invoice.html', {})


# email dispatching
def email_dispatch_detail(request):
    if request.method == "POST":
        honeypot = request.POST.get('phone_verify', '')
        if honeypot != '':
            return JsonResponse({'success': False, 'error': 'Bot detected.'})
        # 1️⃣ Form fields
        email = request.POST.get('email', '').strip()
        selected_option = request.POST.get('selected_option')
        adjusted_pickup_time = request.POST.get('adjusted_pickup_time')
        payment_method = request.POST.get("payment_method")
        payment_amount = request.POST.get('payment_amount')
        remain_first_booking = 'remain_first_booking' in request.POST
        remain_return_booking = 'remain_return_booking' in request.POST
        wait_duration = request.POST.get('wait_duration')
        discount_price = request.POST.get('discount_price')

        # 2️⃣ User 찾기
        user = (
            Post.objects.filter(email__iexact=email).first()
            or Post.objects.filter(email1__iexact=email).first()
            or Inquiry.objects.filter(email__iexact=email).first()
        )

        if not user:
            logger.warning(f"User not found for email: {email}")

        pickup_time_12h = None

        # 3️⃣ Adjusted pickup time 처리
        if adjusted_pickup_time and user:
            users = Post.objects.filter(email=email, pickup_date__gte=date.today()).order_by('pickup_date')
            if users.exists():
                closest_user = users.first()
                closest_user.pickup_time = adjusted_pickup_time
                closest_user.save()

                message = "Important Notice! Please check your email and respond only via email - EasyGo Airport Shuttle"
                if closest_user.contact:
                    send_sms_notice(closest_user.contact, message)

                pickup_time_12h = format_pickup_time_12h(adjusted_pickup_time)

        # 4️⃣ Email template mapping
        template_options = {
            "Gratitude For Payment": ("html_email-response-payment-received.html", "Payment Received - EasyGo"),
            "Pickup Notice for Today": ("html_email-today1.html", "Important Update for Today's Pickup - EasyGo "),
            "Payment Method": ("html_email-response-payment.html", "Payment Method - EasyGo"),
            "PayPal Assistance": ("html_email-response-payment-assistance.html", "PayPal Assistance - EasyGo"),
            "Inquiry for driver contact": ("html_email-response-driver-contact.html", "Inquiry for driver contact - EasyGo"),
            "Airport Pickup Guide": ("html_email-response-arrival-guide.html", "Airport Pickup Guide - EasyGo"),
            'Earlier Pickup Requested for Departure': ("html_email-departure-early.html", "Urgent notice - EasyGo"),
            'Later Pickup Requested for Departure': ("html_email-departure-late.html", "Urgent notice - EasyGo"),
            'Early Arrival Notification': ("html_email-arrival-early.html", "Urgent notice - EasyGo"),
            'Arrival Later Than Scheduled': ("html_email-arrival-late.html", "Urgent notice - EasyGo"),
            'Notice of Delay': ("html_email-just-late-notice.html", "Urgent notice - EasyGo"),
            'Adjusted Pickup Time': ("html_email-just-adjustment.html", "Urgent notice - EasyGo"),
            "Meeting Point Inquiry": ("html_email-response-meeting.html", "Meeting Point - EasyGo"),
            "Payment in Advance Required": ("html_email-response-prepayment.html", "Payment in Advance Required - EasyGo"),
            "Further details for booking": ("html_email-response-more-details.html", "Further details for booking - EasyGo"),
            "Further details for booked": ("html_email-response-details-booked.html", "Further details for booked - EasyGo"),
            "Arrival Pickup Arrangement Without Payment": ("html_email-urgent-arrival-pickup.html", "Arrival Pickup Arrangement Without Payment - EasyGo"),
            "Shared Ride (inquiry) Discount Offer": ("html_email-shared-inquiry-discount.html", "Discount notice - EasyGo"),
            "Shared Ride (booking) Discount Offer": ("html_email-shared-booking-discount.html", "Discount notice - EasyGo"),
            "Cancellation of Booking": ("html_email-response-cancel.html", "Cancellation of Booking: EasyGo"),
            "Apologies Cancellation of Booking": ("html_email-response-cancel1.html", "Apologies Cancellation of Booking: EasyGo"),
            "Cancellation by Client": ("html_email-response-cancelby.html", "Confirmed Booking Cancellation: EasyGo"),
            "Apology for oversight": ("html_email-apology-for-oversight.html", "Apology for oversight: EasyGo"),
            "Payment discrepancy": ("html_email-response-discrepancy.html", "Payment discrepancy: EasyGo"),
            "Special promotion": ("html_email-special-promotion.html", "Special promotion: EasyGo"),
            "Booking delay": ("html_email-booking-delay.html", "Booking delay: EasyGo"),
            "Booking delay 1": ("html_email-booking-delay1.html", "Booking delay 1: EasyGo")
        }

        if selected_option in template_options:
            template_name, subject = template_options[selected_option]

        # 5️⃣ Template 적용
        context = {
            'email': email,
            'name': user.name if user else '',
            'adjusted_pickup_time': adjusted_pickup_time,
            'payment_amount': payment_amount,
            'remain_first_booking': remain_first_booking,    
            'remain_return_booking': remain_return_booking,
            'wait_duration': wait_duration,
            'discount_price': discount_price
        }

        if pickup_time_12h:
            context['pickup_time_12h'] = pickup_time_12h

        # driver info
        if hasattr(user, 'driver') and user.driver:
            context.update({
                'driver': user.driver,
                'driver_name': user.driver.driver_name,
                'driver_contact': user.driver.driver_contact,
                'driver_plate': user.driver.driver_plate,
                'driver_car': user.driver.driver_car,
            })

        # 옵션별 특수 처리
        # ✅ Pickup Notice Today
        if selected_option == "Pickup Notice for Today":
            today = date.today()
            user_today = Post.objects.filter(email=email, pickup_date=today).first()
            if user_today:
                context.update({
                    'pickup_time': user_today.pickup_time,
                    'contact': user_today.contact,
                    'meeting_point': user_today.meeting_point,
                    'direction': user_today.direction,
                    'cash': user_today.cash,
                    'cruise': user_today.cruise,
                    'sms_reminder': user_today.sms_reminder 
                })

        # ✅ Gratitude For Payment
        if selected_option == "Gratitude For Payment":
            try:
                payment_amount = float(payment_amount)
                if payment_amount <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                return JsonResponse({
                    'success': False,
                    'error': "Payment amount must be a number greater than 0."
                }, status=400)

            remaining_amount = payment_amount

            bookings = (
                Post.objects
                .filter(email__iexact=email, pickup_date__gte=date.today())
                .order_by('pickup_date')
            )

            applied_bookings = []

            for booking in bookings:
                price = float(booking.price)
                paid = float(booking.paid or 0)

                # 이미 전액 결제 → 완전히 스킵
                if paid >= price:
                    continue

                due = price - paid
                apply_amount = min(remaining_amount, due)

                # 적용할 금액이 없으면 스킵
                if apply_amount <= 0:
                    continue

                # ✅ 여기부터가 "돈이 실제로 적용된 예약"만
                booking.paid = paid + apply_amount

                original_notice = (booking.notice or "").strip()
                paid_text = f"===Gratitude=== Applied: ${apply_amount}"
                if "===Gratitude===" not in original_notice:
                    booking.notice = (
                        f"{original_notice} | {paid_text}"
                        if original_notice else paid_text
                    )

                booking.reminder = True
                booking.toll = ""
                booking.cash = False
                booking.pending = False
                booking.save()

                applied_bookings.append(booking) 

                remaining_amount -= apply_amount

                if remaining_amount <= 0:
                    break

            context.update({
                'applied_bookings': applied_bookings,
                'payment_amount': payment_amount,
            })

        # ✅ Cancellation
        if selected_option in ["Cancellation of Booking", "Cancellation by Client", "Apologies Cancellation of Booking"]:

            user1 = None
            if user.return_pickup_time == 'x':
                try:
                    user1 = Post.objects.filter(email__iexact=user.email)[1]
                except IndexError:
                    user1 = None

            # 취소 처리
            if user.return_pickup_time == 'x':  # 왕복 예약
                # ① 첫 번째 ❌ / 두 번째 ❌ (모두 취소)
                if not remain_first_booking and not remain_return_booking:
                    user.cancelled = True
                    user.pending = False
                    user.save()

                    if user1:
                        user1.cancelled = True
                        user1.pending = False
                        user1.save()

                # ② 첫 번째 ✅ / 두 번째 ❌
                elif remain_first_booking and not remain_return_booking:
                    user.cancelled = True
                    user.pending = False
                    user.save()

                # ③ 첫 번째 ❌ / 두 번째 ✅
                elif not remain_first_booking and remain_return_booking:
                    if user1:
                        user1.cancelled = True
                        user1.pending = False
                        user1.save()

            else:  # 단일 예약
                user.cancelled = True
                user.pending = False
                user.save()

            # context 업데이트 (한 번만)
            context.update({
                'booking_date': user.pickup_date,
                'return_booking_date': user1.pickup_date if user1 else None,
                'remain_first_booking': remain_first_booking,
                'remain_return_booking': remain_return_booking,
            })

            # Apology SMS
            if selected_option == "Apologies Cancellation of Booking" and user.contact:
                message = (
                    f"EasyGo - Urgent notice!\n\n"
                    f"Dear {user.name}, We have sent an urgent email. Please check your email.\n"
                    "Reply only via email >> info@easygoshuttle.com.au"
                )
                send_sms_notice(user.contact, message)
                send_whatsapp_template(user.contact, user.name)

            # Apology SMS
            if selected_option == "Apologies Cancellation of Booking" and user.contact:
                message = f"EasyGo - Urgent notice!\n\nDear {user.name}, We have sent an urgent email. Please check your email.\nReply only via email >> info@easygoshuttle.com.au"
                send_sms_notice(user.contact, message)
                send_whatsapp_template(user.contact, user.name)


        # ✅ Payment discrepancy
        if selected_option == "Payment discrepancy" and user:
            diff = round(float(user.price) - float(user.paid), 2)
            if diff > 0:
                user.toll = "short payment"
                context.update({'price': user.price, 'paid': user.paid, 'diff': f"{diff:.2f}"})
                user.save()

        # ✅ Payment Confirmed
        if selected_option == "Payment Confirmed":
            if payment_method == "cash":
                user.cash = True
                user.prepay = False
                user.pending = False
                template_name = "html_email-response-cash-payment-confirmed.html"
                subject = "Cash Payment Confirmed - EasyGo"
            elif payment_method == "card":
                user.cash = False
                user.pending = True
                user.prepay = True
                template_name = "html_email-response-card-payment-confirmed.html"
                subject = "Card Payment Confirmed - EasyGo"

            user.reminder = True            
            user.cancelled = False
            user.save()      

            if user.return_pickup_time == 'x':
                user1 = Post.objects.filter(email__iexact=user.email)[1]
                user1.cash = True if payment_method == "cash" else False
                user1.prepay = True if payment_method == "card" else False                
                user1.pending = False if payment_method == "cash" else True
                user1.reminder = True
                user1.cancelled = False
                user1.save()     

        # 6️⃣ Send email
        handle_email_sending(request, email, subject, template_name, context, getattr(user, 'email1', None))

        return render(request, 'basecamp/inquiry_done.html', {
            'google_review_url': settings.GOOGLE_REVIEW_URL,
        })
    
    return render(request, 'basecamp/email/email_dispatch.html', {})


# --------------------------
# PayPal IPN Handler
# --------------------------
PAYPAL_VERIFY_URL = "https://ipnpb.paypal.com/cgi-bin/webscr"

@csrf_exempt
@require_POST
def paypal_ipn(request):
    if request.method == 'POST':        
        item_name = request.POST.get('item_name')
        payer_email = request.POST.get('payer_email')
        gross_amount = request.POST.get('mc_gross')
        txn_id = request.POST.get('txn_id')

        if PaypalPayment.objects.filter(txn_id=txn_id).exists():
            return HttpResponse(status=200, content="Duplicate IPN Notification")
        
        p = PaypalPayment(name=item_name, email=payer_email, amount=gross_amount, txn_id=txn_id)

        try:
            p.save()
        except Exception as e:
            paypal_ipn_error_email('PayPal IPN Error', str(e), item_name, payer_email, gross_amount)
            return HttpResponse(status=500, content="Error processing PayPal IPN")

        ipn_data = request.POST.copy()
        ipn_data['cmd'] = '_notify-validate'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(PAYPAL_VERIFY_URL, data=ipn_data, headers=headers, verify=True)
            response_content = response.text.strip()
            
            if response.status_code == 200 and response_content == 'VERIFIED':
                return HttpResponse(status=200)
            else:
                paypal_ipn_error_email('PayPal IPN Verification Failed', 'Failed to verify PayPal IPN.', item_name, payer_email, gross_amount)
                return HttpResponse(status=500, content="Error processing PayPal IPN")

        except requests.exceptions.RequestException as e:
            paypal_ipn_error_email('PayPal IPN Request Exception', str(e), item_name, payer_email, gross_amount)
            return HttpResponse(status=500, content="Error processing PayPal IPN")

    return HttpResponse(status=400)


# --------------------------
# Stripe Checkout Session
# --------------------------
stripe.api_key = settings.STRIPE_LIVE_SECRET_KEY

@csrf_exempt
@require_POST
def create_stripe_checkout_session(request):
    if request.method == 'POST':
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
            'price': 'price_1PRwKAI9LkpP3oK9hQF7BHj7', 
            'quantity': 1,
            }],
            mode='payment',
            success_url='https://easygoshuttle.com.au/success/',
            cancel_url='https://easygoshuttle.com.au/cancel/',                
        )
        
        return JsonResponse({'id': session.id})
       

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        print('Error parsing payload: {}'.format(str(e)))
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print('Error verifying webhook signature: {}'.format(str(e)))
        return HttpResponse(status=400)

    if event.type == 'checkout.session.completed':
        session = event.data.object
        print('PaymentIntent was successful!')
        handle_checkout_session_completed(session)

    else:
        print(f'Unhandled event type: {event.type}')

    return HttpResponse(status=200)

