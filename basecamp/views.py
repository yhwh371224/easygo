from datetime import datetime, date, timedelta

import logging
from multiprocessing import context
import requests
import stripe
import json

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from main.settings import RECIPIENT_EMAIL, DEFAULT_FROM_EMAIL
from blog.models import Post, Inquiry, PaypalPayment, StripePayment, Driver
from blog.tasks import send_confirm_email, send_email_task, send_notice_email
from blog.sms_utils import send_sms_notice
from basecamp.area import get_suburbs
from basecamp.area_full import get_more_suburbs
from basecamp.area_home import get_home_suburbs

from .utils import parse_date, handle_email_sending, format_pickup_time_12h, render_to_pdf


logger = logging.getLogger(__name__)


def index(request): return redirect('/home/')


def home(request):
    suburbs = get_suburbs()
    home_suburbs = get_home_suburbs()

    if not isinstance(home_suburbs, list):
        home_suburbs = []  # 기본값 설정

    logger.debug(f"home_suburbs: {home_suburbs}") 
    
    fixed_items = [
        "Select your option",
        "Hotels In City",  
        "International Airport",
        "Domestic Airport",
        "WhiteBay cruise terminal",
        "Overseas cruise terminal"
    ]
    
    remaining_items = sorted(
        [item for item in home_suburbs if isinstance(item, str) and item not in fixed_items]
        )
    
    sorted_home_suburbs = fixed_items + remaining_items
    
    # send_notice_email.delay('homepage accessed', 'homepage accessed', RECIPIENT_EMAIL)    
    
    return render(request, 'basecamp/home.html', {
        'suburbs': suburbs,
        'home_suburbs': sorted_home_suburbs,
    })


def about_us(request): 
    # send_notice_email.delay('about_us accessed', 'about_us accessed', RECIPIENT_EMAIL)
    return render(request, 'basecamp/about_us.html')


# Suburb names
def airport_shuttle(request, suburb):
    suburbs = get_suburbs()
    more_suburbs = get_more_suburbs()
    suburb = suburb.replace('-', ' ').title()  
    if suburb in suburbs:
        context = {
            'suburb': suburb,
            'details': suburbs[suburb]
        }
    elif suburb in more_suburbs:
        context = {
            'suburb': suburb, 
            'details': more_suburbs[suburb]
        }
    else:        
        context = {'message': 'Suburb not found'}
        return render(request, 'basecamp/error.html', context)

    return render(request, 'basecamp/airport-shuttle-template.html', context)    


def airport_transfers(request, suburb):
    suburbs = get_suburbs()
    more_suburbs = get_more_suburbs()
    suburb = suburb.replace('-', ' ').title()  
    if suburb in suburbs:
        context = {
            'suburb': suburb,
            'details': suburbs[suburb]
        }
    elif suburb in more_suburbs:
        context = {
            'suburb': suburb, 
            'details': more_suburbs[suburb]
        }
    else:        
        context = {'message': 'Suburb not found'}
        return render(request, 'basecamp/error.html', context)
    
    return render(request, 'basecamp/airport-transfers-template.html', context)


def booking(request):
    context = {
        'RECAPTCHA_V2_SITE_KEY': settings.RECAPTCHA_V2_SITE_KEY,
    }
    return render(request, 'basecamp/booking.html', context)


@login_required
def confirmation(request): 
    return render(request, 'basecamp/confirmation.html')


def confirmation_multiplebookings(request): 
    return render(request, 'basecamp/confirmation_multiplebookings.html')


def confirm_booking(request): 
    return render(request, 'basecamp/confirm_booking.html')


def cruise_booking(request):
    context = {
        'RECAPTCHA_V2_SITE_KEY': settings.RECAPTCHA_V2_SITE_KEY,
    }
    return render(request, 'basecamp/cruise_booking.html', context)


def cruise_inquiry(request):  
    context = {
        'RECAPTCHA_V2_SITE_KEY': settings.RECAPTCHA_V2_SITE_KEY,
    }   
    return render(request, 'basecamp/cruise_inquiry.html', context)


def error(request): 
    return render(request, 'basecamp/error.html')


def email_dispatch(request): 
    return render(request, 'basecamp/email_dispatch.html')


def email_error_confirmbooking(request): 
    return render(request, 'basecamp/email_error_confirmbooking.html')


def home_error(request): 
    return render(request, 'basecamp/home_error.html')


def inquiry(request): 
    context = {
        'RECAPTCHA_V2_SITE_KEY': settings.RECAPTCHA_V2_SITE_KEY,
    }    
    return render(request, 'basecamp/inquiry.html', context)


def inquiry1(request):
    context = {
        'pickup_date': None,
        'direction': None,
        'suburb': None,
        'no_of_passenger': None,
    }    
    return render(request, 'basecamp/inquiry.html', context)


def inquiry2(request): 
    context = {
        'RECAPTCHA_V2_SITE_KEY': settings.RECAPTCHA_V2_SITE_KEY,
    }    
    return render(request, 'basecamp/inquiry2.html', context)


def inquiry_done(request): 
    return render(request, 'basecamp/inquiry_done.html')


def information(request): 
    return render(request, 'basecamp/information.html')


def invoice(request): 
    return render(request, 'basecamp/invoice.html')


def invoice_details(request): 
    return render(request, 'basecamp/invoice_details.html')


def meeting_point(request): 
    return render(request, 'basecamp/meeting_point.html')


def more_suburbs(request): 
    more_suburbs = get_more_suburbs()
    return render(request, 'basecamp/more_suburbs.html', {'more_suburbs': more_suburbs})


def more_suburbs1(request): 
    more_suburbs = get_more_suburbs()
    return render(request, 'basecamp/more_suburbs1.html', {'more_suburbs': more_suburbs})


def payment_cancel(request): 
    return render(request, 'basecamp/payment_cancel.html')


def payment_options(request):
    return render(request, 'basecamp/payment_options.html')


def payment_options1(request): 
    return render(request, 'basecamp/payment_options1.html')


def payonline(request):     
    return render(request, 'basecamp/payonline.html')


def payonline_stripe(request):     
    return render(request, 'basecamp/payonline_stripe.html')


def p2p(request):     
    return render(request, 'basecamp/p2p.html')


def p2p_booking(request): 
    context = {
        'RECAPTCHA_V2_SITE_KEY': settings.RECAPTCHA_V2_SITE_KEY,
    }       
    return render(request, 'basecamp/p2p_booking.html', context)


def p2p_single(request):
    context = {
        'RECAPTCHA_V2_SITE_KEY': settings.RECAPTCHA_V2_SITE_KEY,
    }   
    return render(request, 'basecamp/p2p_single.html', context)


def privacy(request):     
    return render(request, 'basecamp/privacy.html')


def return_cruise_fields(request): 
    return render(request, 'basecamp/return_cruise_fields.html')


def return_flight_fields(request): 
    return render(request, 'basecamp/return_flight_fields.html')


def return_trip(request): 
    return render(request, 'basecamp/return_trip.html')


def return_trip_inquiry(request): 
    return render(request, 'basecamp/return_trip_inquiry.html')


def sending_email_first(request): 
    return render(request, 'basecamp/sending_email_first.html')


def sending_email_second(request): 
    return render(request, 'basecamp/sending_email_second.html')


def sending_email_input_data(request): 
    return render(request, 'basecamp/sending_email_input_data.html')


def service(request):     
    return render(request, 'basecamp/service.html')


def sitemap(request): 
    return render(request, 'basecamp/sitemap.xml')


def success(request): 
    return render(request, 'basecamp/success.html')


def terms(request): 
    return render(request, 'basecamp/terms.html')


def verify_recaptcha(response, version='v2'):
    if version == 'v2':
        secret_key = settings.RECAPTCHA_V2_SECRET_KEY
    elif version == 'v3':
        secret_key = settings.RECAPTCHA_V3_SECRET_KEY
    else:
        return {'success': False, 'error-codes': ['invalid-version']}

    data = {
        'secret': secret_key,
        'response': response
    }
    r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
    return r.json()


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def wrong_date_today(request): 
    return render(request, 'basecamp/wrong_date_today.html')


# Inquiry for airport 
def inquiry_details(request):
    if request.method == "POST":
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

        recaptcha_response = request.POST.get('g-recaptcha-response')
        result = verify_recaptcha(recaptcha_response)
        if not result or not result.get('success'):
            return JsonResponse({'success': False, 'error': 'Invalid reCAPTCHA. Please try the checkbox again.'})  

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
        Pickup date: {pickup_date}
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
        large = int(request.POST.get('baggage_large') or 0)
        medium = int(request.POST.get('baggage_medium') or 0)
        small = int(request.POST.get('baggage_small') or 0)
        baby_seat = int(request.POST.get('baggage_baby') or 0)
        booster_seat = int(request.POST.get('baggage_booster') or 0)
        pram = int(request.POST.get('baggage_pram') or 0)
        ski = int(request.POST.get('baggage_ski') or 0)
        snowboard = int(request.POST.get('baggage_snowboard') or 0)
        golf = int(request.POST.get('baggage_golf') or 0)
        bike = int(request.POST.get('baggage_bike') or 0)
        boxes = int(request.POST.get('baggage_boxes') or 0)
        musical_instrument = int(request.POST.get('baggage_music') or 0)        

        # 🎯 요약 문자열 생성
        baggage_summary = []

        if large: baggage_summary.append(f"L{large}")
        if medium: baggage_summary.append(f"M{medium}")
        if small: baggage_summary.append(f"S{small}")
        if baby_seat: baggage_summary.append(f"Baby{baby_seat}")
        if booster_seat: baggage_summary.append(f"Booster{booster_seat}")
        if pram: baggage_summary.append(f"Pram{pram}")
        if ski: baggage_summary.append(f"Ski{ski}")
        if snowboard: baggage_summary.append(f"Snow{snowboard}")
        if golf: baggage_summary.append(f"Golf{golf}")
        if bike: baggage_summary.append(f"Bike{bike}")
        if boxes: baggage_summary.append(f"Box{boxes}")
        if musical_instrument: baggage_summary.append(f"Music{musical_instrument}")
        
        # 🧾 최종 요약 문자열
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
            return render(request, 'basecamp/inquiry_done.html')
        
    else:
        return render(request, 'basecamp/inquiry.html', {})


# inquiry (simple one) for airport from home page
def inquiry_details1(request):
    if request.method == "POST":
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
        Flight date: {pickup_date}
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

        if original_start_point == 'International Airport':
            direction = 'Pickup from Intl Airport'
            suburb = original_end_point # end_point 대신 original_end_point 사용
            start_point = ''
            end_point = ''
        elif original_start_point == 'Domestic Airport':
            direction = 'Pickup from Domestic Airport'
            suburb = original_end_point # end_point 대신 original_end_point 사용
            start_point = ''
            end_point = ''
        elif original_end_point == 'International Airport':
            direction = 'Drop off to Intl Airport'
            suburb = original_start_point # start_point 대신 original_start_point 사용
            end_point = ''
            start_point = ''
        elif original_end_point == 'Domestic Airport':
            direction = 'Drop off to Domestic Airport'
            suburb = original_start_point # start_point 대신 original_start_point 사용
            end_point = ''
            start_point = ''
        
        # 6. 개별 수하물 항목 수집 및 요약 (기존 로직 유지)
        large = int(request.POST.get('baggage_large') or 0)
        medium = int(request.POST.get('baggage_medium') or 0)
        small = int(request.POST.get('baggage_small') or 0)
        baby_seat = int(request.POST.get('baggage_baby') or 0)
        booster_seat = int(request.POST.get('baggage_booster') or 0)
        pram = int(request.POST.get('baggage_pram') or 0)
        ski = int(request.POST.get('baggage_ski') or 0)
        snowboard = int(request.POST.get('baggage_snowboard') or 0)
        golf = int(request.POST.get('baggage_golf') or 0)
        bike = int(request.POST.get('baggage_bike') or 0)
        boxes = int(request.POST.get('baggage_boxes') or 0)
        musical_instrument = int(request.POST.get('baggage_music') or 0)        

        baggage_summary = []
        if large: baggage_summary.append(f"L{large}")
        if medium: baggage_summary.append(f"M{medium}")
        if small: baggage_summary.append(f"S{small}")
        if baby_seat: baggage_summary.append(f"Baby{baby_seat}")
        if booster_seat: baggage_summary.append(f"Booster{booster_seat}")
        if pram: baggage_summary.append(f"Pram{pram}")
        if ski: baggage_summary.append(f"Ski{ski}")
        if snowboard: baggage_summary.append(f"Snow{snowboard}")
        if golf: baggage_summary.append(f"Golf{golf}")
        if bike: baggage_summary.append(f"Bike{bike}")
        if boxes: baggage_summary.append(f"Box{boxes}")
        if musical_instrument: baggage_summary.append(f"Music{musical_instrument}")
        
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

        return render(request, 'basecamp/inquiry_done.html')

    else:
        return redirect('basecamp:home')


# Contact form
def inquiry_details2(request):
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email') 
        pickup_date = request.POST.get('pickup_date')     
        message = request.POST.get('message')  
        
        recaptcha_response = request.POST.get('g-recaptcha-response')
        result = verify_recaptcha(recaptcha_response)
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': 'Invalid reCAPTCHA. Please try the checkbox again.'}) 

        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'pickup_date': pickup_date,
            'message': message}
        
        today = date.today()
        if pickup_date != str(today):
            if is_ajax(request):
                return render(request, 'basecamp/wrong_date_today.html')
            else:
                return render(request, 'basecamp/wrong_date_today.html')
                     
        message_template = '''
        Contact Form
        =====================
        name: {name}
        contact: {contact}        
        email: {email}
        flight date: {pickup_date}
        message: {message}              
        '''
        message = message_template.format(**data)

        subject = f"[New Contact] Submission from {data['name']}"

        send_mail(subject, message, '', [RECIPIENT_EMAIL])
        
        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
        else:
            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/inquiry2.html', {})
    
    
# Multiple points Inquiry 
def p2p_detail(request):    
    if request.method == "POST":
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

        
        recaptcha_response = request.POST.get('g-recaptcha-response')
        result = verify_recaptcha(recaptcha_response)
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': 'Invalid reCAPTCHA. Please try the checkbox again.'}) 
        
        # ✅ 중복 제출 방지 
        recent_duplicate = Inquiry.objects.filter(
            email=p2p_email,
            created__gte=timezone.now() - timedelta(seconds=2)
        ).exists()

        if recent_duplicate:
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})  

        subject = "Multiple points inquiry"
        template_name = "basecamp/html_email-p2p.html"

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
            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/p2p.html', {})
    

# p2p multiple points booking by myself 
def p2p_booking_detail(request):    
    if request.method == "POST":
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
        template_name = "basecamp/html_email-p2p-confirmation.html"

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
            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/p2p.html', {})


def price_detail(request):
    if request.method == "POST":
        pickup_date_str = request.POST.get('pickup_date', '')  
        start_point = request.POST.get('start_point')
        end_point = request.POST.get('end_point')
        no_of_passenger = request.POST.get('no_of_passenger')
        
        # 1. 'Select your option' 검증
        if start_point == 'Select your option' or end_point == 'Select your option':
            return render(request, 'basecamp/home_error.html')

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

        if start_point in ['International Airport', 'Domestic Airport']:
            normalized_start_point = 'Airport'

        if end_point in ['International Airport', 'Domestic Airport']:
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

        return render(request, 'basecamp/inquiry1.html', context)

    else:
        suburbs = get_suburbs()
        home_suburbs = get_home_suburbs()

        return render(request, 'basecamp/home.html', {
            'suburbs': suburbs,
            'home_suburbs': home_suburbs,
        })
    

def to_bool(value):
    return str(value).lower() in ["true", "1", "on", "yes"]


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
            'pickup_date': pickup_date_obj.strftime('%Y-%m-%d')}       
        
        inquiry_email = Inquiry.objects.filter(email=email).exists()
        post_email = Post.objects.filter(email=email).exists()  

        email_content_template = '''
        Hello, {name} \n
        {status_message}\n 
        *** It starts from Home Page
        =============================
        Contact: {contact}
        Email: {email}  
        Flight date: {pickup_date}
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
        large = int(request.POST.get('baggage_large') or 0)
        medium = int(request.POST.get('baggage_medium') or 0)
        small = int(request.POST.get('baggage_small') or 0)
        baby_seat = int(request.POST.get('baggage_baby') or 0)
        booster_seat = int(request.POST.get('baggage_booster') or 0)
        pram = int(request.POST.get('baggage_pram') or 0)
        ski = int(request.POST.get('baggage_ski') or 0)
        snowboard = int(request.POST.get('baggage_snowboard') or 0)
        golf = int(request.POST.get('baggage_golf') or 0)
        bike = int(request.POST.get('baggage_bike') or 0)
        boxes = int(request.POST.get('baggage_boxes') or 0)
        musical_instrument = int(request.POST.get('baggage_music') or 0)        

        # 🎯 요약 문자열 생성
        baggage_summary = []

        if large: baggage_summary.append(f"L{large}")
        if medium: baggage_summary.append(f"M{medium}")
        if small: baggage_summary.append(f"S{small}")
        if baby_seat: baggage_summary.append(f"Baby{baby_seat}")
        if booster_seat: baggage_summary.append(f"Booster{booster_seat}")
        if pram: baggage_summary.append(f"Pram{pram}")
        if ski: baggage_summary.append(f"Ski{ski}")
        if snowboard: baggage_summary.append(f"Snow{snowboard}")
        if golf: baggage_summary.append(f"Golf{golf}")
        if bike: baggage_summary.append(f"Bike{bike}")
        if boxes: baggage_summary.append(f"Box{boxes}")
        if musical_instrument: baggage_summary.append(f"Music{musical_instrument}")
        
        # 🧾 최종 요약 문자열
        baggage_str = ", ".join(baggage_summary)

        p = Post(company_name=company_name, name=name, contact=contact, email=email, email1=email1, pickup_date=pickup_date_obj, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, start_point=start_point, end_point=end_point, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=baggage_str, message=message, return_direction=return_direction, return_pickup_date=return_pickup_date_obj, 
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, return_pickup_time=return_pickup_time, return_start_point=return_start_point,
                 return_end_point=return_end_point, notice=notice, price=price, paid=paid, cash=cash, prepay=prepay, driver=sam_driver)
        
        p.save()

        rendering = render(request, 'basecamp/inquiry_done.html')   
        
        template_name = "basecamp/html_email-confirmation.html"

        context = {
            'company_name': company_name, 'name': name, 'contact': contact, 
            'email': email, 'email1': email1, 'pickup_date': pickup_date_obj, 
            'flight_number': flight_number, 'flight_time': flight_time, 'pickup_time': pickup_time, 
            'start_point': start_point, 'end_point': end_point, 'return_direction': return_direction,
            'return_pickup_date': return_pickup_date_obj, 'return_flight_number': return_flight_number, 
            'return_flight_time': return_flight_time, 'return_pickup_time': return_pickup_time, 
            'return_start_point': return_start_point, 'return_end_point': return_end_point, 
            'direction': direction, 'street': street, 'suburb': suburb, 
            'no_of_passenger': no_of_passenger, 'no_of_baggage': baggage_str, 'message': message, 
            'notice': notice, 'price': price, 'cash': cash, 'paid': paid
        }

        customer_subject = "Booking Confirmation - EasyGo Airport Shuttle" 

        handle_email_sending(request, email, customer_subject, template_name, context, email1=email1)
        
        return rendering

    else:
        return render(request, 'basecamp/confirmation.html', {})


# airport booking by client
def booking_detail(request):
    if request.method == "POST":   
        # ✅ Collect date strings
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

        recaptcha_response = request.POST.get('g-recaptcha-response')
        result = verify_recaptcha(recaptcha_response)
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': 'Invalid reCAPTCHA. Please try the checkbox again.'}) 
        
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
        large = int(request.POST.get('baggage_large') or 0)
        medium = int(request.POST.get('baggage_medium') or 0)
        small = int(request.POST.get('baggage_small') or 0)
        baby_seat = int(request.POST.get('baggage_baby') or 0)
        booster_seat = int(request.POST.get('baggage_booster') or 0)
        pram = int(request.POST.get('baggage_pram') or 0)
        ski = int(request.POST.get('baggage_ski') or 0)
        snowboard = int(request.POST.get('baggage_snowboard') or 0)
        golf = int(request.POST.get('baggage_golf') or 0)
        bike = int(request.POST.get('baggage_bike') or 0)
        boxes = int(request.POST.get('baggage_boxes') or 0)
        musical_instrument = int(request.POST.get('baggage_music') or 0)        

        # 🎯 요약 문자열 생성
        baggage_summary = []

        if large: baggage_summary.append(f"L{large}")
        if medium: baggage_summary.append(f"M{medium}")
        if small: baggage_summary.append(f"S{small}")
        if baby_seat: baggage_summary.append(f"Baby{baby_seat}")
        if booster_seat: baggage_summary.append(f"Booster{booster_seat}")
        if pram: baggage_summary.append(f"Pram{pram}")
        if ski: baggage_summary.append(f"Ski{ski}")
        if snowboard: baggage_summary.append(f"Snow{snowboard}")
        if golf: baggage_summary.append(f"Golf{golf}")
        if bike: baggage_summary.append(f"Bike{bike}")
        if boxes: baggage_summary.append(f"Box{boxes}")
        if musical_instrument: baggage_summary.append(f"Music{musical_instrument}")
        
        # 🧾 최종 요약 문자열
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
            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/booking.html', {})
    

# cruise booking by client
def cruise_booking_detail(request):
    if request.method == "POST": 
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

        recaptcha_response = request.POST.get('g-recaptcha-response')
        result = verify_recaptcha(recaptcha_response)
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': 'Invalid reCAPTCHA. Please try the checkbox again.'}) 
        
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
        large = int(request.POST.get('baggage_large') or 0)
        medium = int(request.POST.get('baggage_medium') or 0)
        small = int(request.POST.get('baggage_small') or 0)
        baby_seat = int(request.POST.get('baggage_baby') or 0)
        booster_seat = int(request.POST.get('baggage_booster') or 0)
        pram = int(request.POST.get('baggage_pram') or 0)
        ski = int(request.POST.get('baggage_ski') or 0)
        snowboard = int(request.POST.get('baggage_snowboard') or 0)
        golf = int(request.POST.get('baggage_golf') or 0)
        bike = int(request.POST.get('baggage_bike') or 0)
        boxes = int(request.POST.get('baggage_boxes') or 0)
        musical_instrument = int(request.POST.get('baggage_music') or 0)        

        # 🎯 요약 문자열 생성
        baggage_summary = []

        if large: baggage_summary.append(f"L{large}")
        if medium: baggage_summary.append(f"M{medium}")
        if small: baggage_summary.append(f"S{small}")
        if baby_seat: baggage_summary.append(f"Baby{baby_seat}")
        if booster_seat: baggage_summary.append(f"Booster{booster_seat}")
        if pram: baggage_summary.append(f"Pram{pram}")
        if ski: baggage_summary.append(f"Ski{ski}")
        if snowboard: baggage_summary.append(f"Snow{snowboard}")
        if golf: baggage_summary.append(f"Golf{golf}")
        if bike: baggage_summary.append(f"Bike{bike}")
        if boxes: baggage_summary.append(f"Box{boxes}")
        if musical_instrument: baggage_summary.append(f"Music{musical_instrument}")
        
        # 🧾 최종 요약 문자열
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
            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/cruise_booking.html', {})


def confirm_booking_detail(request):
    if request.method == "POST":
        email = request.POST.get('email')
        is_confirmed = request.POST.get('is_confirmed') == 'True'
        index = request.POST.get('index', '1')

        try:
            index = int(index) - 1  
        except ValueError:
            return HttpResponse("Invalid index value", status=400)  
        
        users = Inquiry.objects.filter(email__iexact=email)

        if users.exists() and 0 <= index < len(users):
            user = users[index]
        else:
            return render(request, 'basecamp/email_error_confirmbooking.html')

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
        cash = user.cash 
        prepay = user.prepay    

        try:
            pickup_date_obj = parse_date(
                pickup_date, 
                field_name="Pickup Date", 
                required=True
            )

            return_pickup_date_obj = parse_date(
                return_pickup_date, 
                field_name="Return Pickup Date", 
                required=False, 
                reference_date=pickup_date
            )

        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})    
        
        # 최종 가격 계산
        try:
            final_price = float(price) + float(toll)
        except Exception:
            final_price = price  # 혹시 변환 에러 시 원래 price만 저장
        
        toll_value = "toll included" if toll else ""

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
            price=final_price, toll=toll_value, prepay=prepay, 
            paid=paid, cash=cash, is_confirmed=is_confirmed, driver=sam_driver
        )
        
        p.save()    
        user.delete()
                
        return render(request, 'basecamp/inquiry_done.html') 
        
    else:
        return render(request, 'basecamp/confirm_booking.html', {}) 

     
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

            # ✅ Only update prepay if it’s provided
            if prepay_raw is not None:
                user.prepay = (prepay_raw == 'True')

            if cash_raw is not None:
                user.cash = (cash_raw == 'True')  

            user.sent_email = True
            user.save()
            
            if user.cancelled: 
                template_name = "basecamp/html_email-cancelled.html"
                subject = "Booking Cancellation Notice - EasyGo" 
                
                context = {
                    'name': user.name, 
                    'email': user.email 
                }

                handle_email_sending(request, user.email, subject, template_name, context)
                    
            else: 
                # ✅ Now use the final saved value of user.prepay and company_name
                if user.prepay or (user.company_name or "").strip():
                    template_name = "basecamp/html_email-confirmation-1.html"
                elif user.pending:
                    template_name = "basecamp/html_email-confirmation-pending.html"
                else:
                    template_name = "basecamp/html_email-confirmation.html"

                html_content = render_to_string("basecamp/html_email-confirmation.html", 
                                        {'company_name': user.company_name, 'name': user.name, 'contact': user.contact, 'email': user.email, 'email1': user.email1,
                                            'pickup_date': user.pickup_date, 'flight_number': user.flight_number,
                                            'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                            'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                            'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                            'return_direction': user.return_direction, 'return_pickup_date': user.return_pickup_date, 
                                            'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                                            'return_pickup_time': user.return_pickup_time,'message': user.message, 'notice': user.notice, 
                                            'price': user.price, 'paid': user.paid, 'cash': user.cash})
            
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives(
                    "Booking confirmation - EasyGo",
                    text_content,
                    '',
                    [email, RECIPIENT_EMAIL]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                
                # subject = "Booking confirmation - EasyGo" # 제목도 기존 로직에서 가져옴

                # # 템플릿에 전달할 컨텍스트 딕셔너리 구성
                # context = {
                #     'company_name': user.company_name, 'name': user.name, 'contact': user.contact, 
                #     'email': user.email, 'email1': user.email1, 'pickup_date': user.pickup_date, 
                #     'flight_number': user.flight_number, 'flight_time': user.flight_time, 'pickup_time': user.pickup_time, 
                #     'start_point': user.start_point, 'end_point': user.end_point, 'direction': user.direction, 
                #     'street': user.street, 'suburb': user.suburb, 'no_of_passenger': user.no_of_passenger, 
                #     'no_of_baggage': user.no_of_baggage, 'return_direction': user.return_direction, 
                #     'return_pickup_date': user.return_pickup_date, 'return_flight_number': user.return_flight_number, 
                #     'return_flight_time': user.return_flight_time, 'return_pickup_time': user.return_pickup_time, 
                #     'return_start_point': user.return_start_point, 'return_end_point': user.return_end_point, 
                #     'message': user.message, 'notice': user.notice, 'price': user.price, 
                #     'toll': user.toll, 'paid': user.paid, 'cash': user.cash,
                # }

                # handle_email_sending(request, user.email, subject, template_name, context, email1=user.email1)

            return render(request, 'basecamp/inquiry_done.html')  
        
        else:            
            return HttpResponse("No user found", status=400)

    else:
        return render(request, 'basecamp/sending_email_first.html', {})
    

# sending confirmation email second one    
def sending_email_second_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        prepay_raw = request.POST.get('prepay')  # May be None
        cash_raw = request.POST.get('cash') # May be Nonne

        user = Post.objects.filter(email__iexact=email)[1]
        user1 = Post.objects.filter(email__iexact=email).first() 

        # ✅ Only update prepay if it’s provided
        if prepay_raw is not None:
            user.prepay = (prepay_raw == 'True')

        if cash_raw is not None:
            user.cash = (cash_raw == 'True')   

        user.sent_email = True
        user.save()  

        double_price = float(user.price or 0) * 2
        if user.paid:
            double_paid = float(user.paid) * 2
        else:
            double_paid = None
        
        if user.cancelled: 
            template_name = "basecamp/html_email-cancelled.html"
            subject = "Booking Cancellation Notice - EasyGo" 
            
            context = {
                'name': user.name, 
                'email': user.email 
            }

            handle_email_sending(request, user.email, subject, template_name, context)

        else:
            # ✅ Now use the final saved value of user.prepay and company_name
            if user.prepay or (user.company_name or "").strip():
                template_name = "basecamp/html_email-confirmation-1.html"
            elif user.pending:
                    template_name = "basecamp/html_email-confirmation-pending.html"
            else:
                template_name = "basecamp/html_email-confirmation.html"

            context = {
                'company_name': user.company_name, 'name': user.name, 'contact': user.contact, 
                'email': user.email, 'email1': user.email1, 'pickup_date': user.pickup_date, 
                'flight_number': user.flight_number, 'flight_time': user.flight_time, 'pickup_time': user.pickup_time, 
                'start_point': user.start_point, 'end_point': user.end_point, 'direction': user.direction, 
                'street': user.street, 'suburb': user.suburb, 'no_of_passenger': user.no_of_passenger, 
                'no_of_baggage': user.no_of_baggage, 'return_direction': user.return_direction, 
                'return_pickup_date': user.return_pickup_date, 'return_flight_number': user.return_flight_number, 
                'return_flight_time': user.return_flight_time, 'return_pickup_time': user.return_pickup_time, 
                'return_start_point': user.return_start_point, 'return_end_point': user.return_end_point, 
                'message': user.message, 'notice': user.notice, 'price': double_price, 
                'toll': user.toll, 'paid': double_paid, 'cash': user.cash,
            }

            subject = "Booking confirmation - EasyGo" 
            handle_email_sending(request, user.email, subject, template_name, context, email1=user.email1)

        if not user1.sent_email: 
            user1.sent_email = True
            user1.save()
            
        return render(request, 'basecamp/inquiry_done.html') 
    
    else:
        return render(request, 'basecamp/sending_email_second.html', {})
    

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
            template_name = "basecamp/html_email-input-date.html"
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


        return render(request, 'basecamp/inquiry_done.html') 
    
    else:
        return render(request, 'basecamp/sending_email_first.html', {})   

def to_bool(value):
    return str(value).lower() in ["true", "1", "on", "yes"]


# For Return Trip 
def return_trip_detail(request):     
    if request.method == "POST":
        # ✅ Collect date strings
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

        subject = f"[New Return Trip] Submission from {data['name']} ({data['pickup_date']})"

        send_mail(subject, content, '', [RECIPIENT_EMAIL])
         
        sam_driver = Driver.objects.get(driver_name="Sam")  
                    
        p = Post(name=name, company_name=company_name, contact=contact, email=email, pickup_date=pickup_date_obj, flight_number=flight_number, flight_time=flight_time, 
                 pickup_time=pickup_time, start_point=start_point, end_point=end_point, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, cash=cash, prepay=prepay, return_direction=return_direction, 
                 return_pickup_date=return_pickup_date_obj, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, return_start_point=return_start_point, return_end_point=return_end_point, driver=sam_driver,
                 price=price, toll=toll)
        
        p.save()

        rendering = render(request, 'basecamp/inquiry_done.html')    
        
        return rendering
    
    else:
        return render(request, 'basecamp/return_trip.html', {})  


# 안전한 float 변환 함수 (inc toll 같은 것도 처리)
def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        if value and 'inc' in value.lower():
            return 0.0
        return None

def invoice_detail(request):
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        extra_email = request.POST.get('extra_email', '').strip()  # ← 새 필드
        surcharge_flag = request.POST.get('surcharge')
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
            
        # Multi booking 여부
        multiple = False
        if from_date and to_date:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            bookings = users.filter(pickup_date__range=(from_date_obj, to_date_obj)).order_by('pickup_date', 'pickup_time')
            multiple = True
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
                    if "Drop off to Domestic" in booking.direction:
                        start_point = f"{booking.street}, {booking.suburb}"
                        end_point = "Domestic Airport"
                    elif "Drop off to Intl" in booking.direction:
                        start_point = f"{booking.street}, {booking.suburb}"
                        end_point = "International Airport"
                    elif "Pickup from Domestic" in booking.direction:
                        start_point = "Domestic Airport"
                        end_point = f"{booking.street}, {booking.suburb}"
                    elif "Pickup from Intl" in booking.direction:
                        start_point = "International Airport"
                        end_point = f"{booking.street}, {booking.suburb}"
                    else:
                        start_point = "Unknown"
                        end_point = "Unknown" 

                price = safe_float(booking.price) or 0.0
                with_gst = round(price * 0.10, 2) if booking.company_name else 0.0
                surcharge = round(price * 0.03, 2) if surcharge_flag else 0.0
                toll = safe_float(toll_input) if toll_input else safe_float(booking.toll) or 0.0  
                paid = safe_float(booking.paid) or 0.0              

                total = price + with_gst + surcharge + toll 
                
                total_price_without_gst += price
                total_gst += with_gst
                total_surcharge += surcharge
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
                    "surcharge": surcharge,
                    "toll": toll,
                    "total_price": total,
                })
                
            
            if (discount_input or '') == 'Yes':
                    discount = 0.0
            elif (discount_input or '').replace('.', '', 1).isdigit():
                discount = float(discount_input)
            elif (bookings[0].discount or '').replace('.', '', 1).isdigit():
                discount = float(bookings[0].discount)
            else:
                discount = 0.0

            final_total = grand_total - discount
            total_balance = round(final_total - total_paid, 2)

            context = {
                "inv_no": inv_no,
                "company_name": bookings[0].company_name,
                "name": bookings[0].name,
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
            }

            template_name = "basecamp/html_email-multi-invoice.html"
            html_content = render_to_string(template_name, context)

        else:
            user = bookings[0]
            
            start_point = user.start_point
            end_point = user.end_point

            price = safe_float(user.price) or 0.0
            with_gst = round(price * 0.10, 2) if user.company_name else 0.0
            float_surcharge = round(price * 0.03, 2) if surcharge_flag else 0.0
            toll = safe_float(toll_input) if toll_input else safe_float(user.toll) or 0.0            
            
            if (discount_input or '') == 'Yes':
                discount = 0.0
            elif (discount_input or '').replace('.', '', 1).isdigit():
                discount = float(discount_input)
            elif (user.discount or '').replace('.', '', 1).isdigit():
                discount = float(user.discount)
            else:
                discount = 0.0

            total_price = price + with_gst + float_surcharge + toll - discount
            float_paid = safe_float(user.paid) or 0.0
            balance = round(total_price - float_paid, 2)

            if user.cash and user.paid:
                cash_balance = balance - (with_gst + float_surcharge)
                template_name = "basecamp/html_email-invoice-cash.html"
                context = {
                    "inv_no": inv_no, "name": user.name, "company_name": user.company_name,
                    "contact": user.contact, "discount": discount, "email": email,
                    "pickup_date": user.pickup_date, "pickup_time": user.pickup_time,    
                    "start_point": start_point, "end_point": end_point, "invoice_date": today,
                    "price": user.price, "with_gst": with_gst, "surcharge": float_surcharge,
                    "total_price": total_price, "toll": toll, "balance": cash_balance, 
                    "paid": float_paid, "message": user.message, "no_of_passenger": user.no_of_passenger,
                    "no_of_baggage": user.no_of_baggage, "notice": user.notice, "street": user.street, "suburb": user.suburb,
                    "return_pickup_time": user.return_pickup_time, "return_pickup_date": user.return_pickup_date,
                }

            elif user.return_pickup_time == "x":
                user1 = Post.objects.filter(email__iexact=email)[1]

                # 두 배 가격 계산
                base_price = safe_float(user1.price) or 0.0
                base_paid = safe_float(user1.paid) or 0.0

                doubled_price = base_price * 2
                doubled_paid = base_paid * 2  
                doubled_with_gst = round(doubled_price * 0.10, 2) if user1.company_name else 0.0
                doubled_surcharge = round(doubled_price * 0.03, 2) if surcharge_flag else 0.0
                doubled_total = doubled_price + doubled_with_gst + doubled_surcharge + toll - discount
                balance = round(doubled_total - doubled_paid, 2)

                template_name = "basecamp/html_email-invoice.html"
                context = {
                    "inv_no": inv_no, "name": user1.name, "company_name": user1.company_name,
                    "contact": user1.contact, "pickup_date": user1.pickup_date, "pickup_time": user1.pickup_time,   
                    "start_point": user1.start_point, "end_point": user1.end_point, "invoice_date": today,
                    "price": doubled_price, "with_gst": doubled_with_gst, "surcharge": doubled_surcharge,
                    "total_price": doubled_total, "toll": toll, "balance": balance, "discount": discount,
                    "paid": doubled_paid, "message": user1.message, "no_of_passenger": user1.no_of_passenger,
                    "no_of_baggage": user1.no_of_baggage, "notice": user1.notice, "street": user1.street, "suburb": user1.suburb,
                    "return_pickup_time": user1.return_pickup_time, "return_pickup_date": user1.return_pickup_date,
                }
            else:
                template_name = "basecamp/html_email-invoice.html"
                context = {
                    "inv_no": inv_no, "name": user.name, "company_name": user.company_name,
                    "contact": user.contact, "pickup_date": user.pickup_date, "pickup_time": user.pickup_time,  
                    "start_point": start_point, "end_point": end_point, "invoice_date": today,
                    "price": user.price, "with_gst": with_gst, "surcharge": float_surcharge,
                    "total_price": total_price, "toll": toll, "balance": balance, "discount": discount,
                    "paid": float_paid, "message": user.message, "no_of_passenger": user.no_of_passenger,
                    "no_of_baggage": user.no_of_baggage, "notice": user.notice, "street": user.street, "suburb": user.suburb,
                    "return_pickup_time": user.return_pickup_time, "return_pickup_date": user.return_pickup_date,
                }

            html_content = render_to_string(template_name, context)

        text_content = strip_tags(html_content)
        recipient_list = [email, RECIPIENT_EMAIL]
        if extra_email:                # 값이 있으면 추가
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
            if not user.cash:  # 🚨 cash인 경우는 제외
                user.price = round(float(user.price) * 1.10, 2)
                user.prepay = True
                user.save()

        return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/invoice.html', {})


# email dispatching
def email_dispatch_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email', '').strip() 
        selected_option = request.POST.get('selected_option')      
        adjustment_time = request.POST.get('adjustment_time')
        wait_duration = request.POST.get('wait_duration')
        discount_price = request.POST.get('discount_price')        
        
        user = Post.objects.filter(email__iexact=email).first()
        if not user:
            user = Post.objects.filter(email1=email).first()
        if not user:
            user = Inquiry.objects.filter(email__iexact=email).first()

        # Handle adjustment_time logic (DB update + SMS + context prep)
        pickup_time_12h = None
        if adjustment_time and user:
            users = Post.objects.filter(email=email, pickup_date__gte=date.today()).order_by('pickup_date')
            if users.exists():
                closest_user = users.first()
                closest_user.pickup_time = adjustment_time
                closest_user.save()

                message = "Important Notice! Please check your email and respond only via email - EasyGo Airport Shuttle"
                send_sms_notice(closest_user.contact, message)

                pickup_time_12h = format_pickup_time_12h(adjustment_time)                       
        
        template_options = {
            "Gratitude For Payment": ("basecamp/html_email-response-payment-received.html", "Payment Received - EasyGo"),
            "Gratitude For (M) Payment": ("basecamp/html_email-response-multi-payment-received.html", "(M) Payment Received - EasyGo"),
            "Cash Payment Confirmed": ("basecamp/html_email-response-cash-payment-confirmed.html", "Cash Payment Confirmed - EasyGo"),
            "Pickup Notice for Today": ("basecamp/html_email-today1.html", "Important Update for Today's Pickup - EasyGo "),
            "Payment Method": ("basecamp/html_email-response-payment.html", "Payment Method - EasyGo"),
            "PayPal Assistance": ("basecamp/html_email-response-payment-assistance.html", "PayPal Assistance - EasyGo"),
            "Inquiry for driver contact": ("basecamp/html_email-response-driver-contact.html", "Inquiry for driver contact - EasyGo"),
            "Airport Pickup Guide": ("basecamp/html_email-response-arrival-guide.html", "Airport Pickup Guide - EasyGo"),
            'Earlier Pickup Requested for Departure': ("basecamp/html_email-departure-early.html", "Urgent notice - EasyGo"),
            'Later Pickup Requested for Departure': ("basecamp/html_email-departure-late.html", "Urgent notice - EasyGo"),
            'Early Arrival Notification': ("basecamp/html_email-arrival-early.html", "Urgent notice - EasyGo"),
            'Arrival Later Than Scheduled': ("basecamp/html_email-arrival-late.html", "Urgent notice - EasyGo"),
            'Notice of Delay': ("basecamp/html_email-just-late-notice.html", "Urgent notice - EasyGo"),
            'Adjusted Pickup Time': ("basecamp/html_email-just-adjustment.html", "Urgent notice - EasyGo"),            
            "Meeting Point Inquiry": ("basecamp/html_email-response-meeting.html", "Meeting Point - EasyGo"),  
            "Payment in Advance Required": ("basecamp/html_email-response-prepayment.html", "Payment in Advance Required - EasyGo"),           
            "Further details for booking": ("basecamp/html_email-response-more-details.html", "Further details for booking - EasyGo"),
            "Further details for booked": ("basecamp/html_email-response-details-booked.html", "Further details for booked - EasyGo"),
            "Arrival Pickup Arrangement Without Payment": ("basecamp/html_email-urgent-arrival-pickup.html", "Arrival Pickup Arrangement Without Payment - EasyGo"),
            "Shared Ride (inquiry) Discount Offer": ("basecamp/html_email-shared-inquiry-discount.html", "Discount notice - EasyGo"),
            "Shared Ride (booking) Discount Offer": ("basecamp/html_email-shared-booking-discount.html", "Discount notice - EasyGo"),
            "Cancellation of Booking": ("basecamp/html_email-response-cancel.html", "Cancellation of Booking: EasyGo"),
            "Apologies Cancellation of Booking": ("basecamp/html_email-response-cancel1.html", "Apologies Cancellation of Booking: EasyGo"),
            "Cancellation by Client": ("basecamp/html_email-response-cancelby.html", "Confirmed Booking Cancellation: EasyGo"),
            "Apology for oversight": ("basecamp/html_email-apology-for-oversight.html", "Apology for oversight: EasyGo"),
            "Payment discrepancy": ("basecamp/html_email-response-discrepancy.html", "Payment discrepancy: EasyGo"),
            "Special promotion": ("basecamp/html_email-special-promotion.html", "Special promotion: EasyGo"),
            "Booking delay": ("basecamp/html_email-booking-delay.html", "Booking delay: EasyGo"),
            "Booking delay 1": ("basecamp/html_email-booking-delay1.html", "Booking delay 1: EasyGo")
        }

        if selected_option in template_options:
            template_name, subject = template_options[selected_option]
            context = {'email': email, 'name': user.name, 'adjustment_time': adjustment_time, 'wait_duration': wait_duration, 'discount_price': discount_price}

            if pickup_time_12h:
                context['pickup_time_12h'] = pickup_time_12h

            # driver 정보 추가
            if user and hasattr(user, 'driver') and user.driver:
                context.update({
                    'driver': user.driver,
                    'driver_name': user.driver.driver_name,
                    'driver_contact': user.driver.driver_contact,
                    'driver_plate': user.driver.driver_plate,
                    'driver_car': user.driver.driver_car,
                })

            if selected_option == "Pickup Notice for Today" and user:
                today = date.today()
                user_today = Post.objects.filter(email=email, pickup_date=today).first()
                if user_today:
                    context.update({
                        'pickup_time': user_today.pickup_time,
                        'meeting_point': user_today.meeting_point,
                        'direction': user_today.direction,
                        'cash': user_today.cash,
                        'cruise': user_today.cruise,
                    })

            if selected_option == "Gratitude For Payment" and user:
                original_price = float(user.price or 0)   
                original_notice = (user.notice or "").strip()

                has_payment_record = any(keyword in original_notice for keyword in ["===STRIPE===", "===PAYPAL===", "===Gratitude==="])                

                # 왕복 픽업 있는 경우
                if user.return_pickup_time == 'x':
                    full_price = original_price * 2
                    if user.email1:
                        full_price += full_price * 0.1  # 전체 왕복 요금에 10% 추가

                    total_paid_text_full = f"===Gratitude=== Total Paid: ${int(full_price)}"

                    if not has_payment_record:
                        user.notice = (
                            f"{original_notice} | {total_paid_text_full}"
                            if original_notice else total_paid_text_full
                        )
                    else:
                        user.notice = original_notice

                    user.paid = user.price
                    user.reminder = True
                    user.toll = ""
                    user.cash = False
                    user.pending = False
                    user.save()

                    context.update({
                        'pickup_date': user.pickup_date,
                        'price': full_price,
                        'return_pickup_date': user.return_pickup_date if user else '',
                    })

                    try:
                        user_1 = Post.objects.filter(email=user.email)[1]
                        user_1_price = original_price * 2
                        if user.email1:
                            user_1_price += user_1_price * 0.1  # 10% 추가

                        user_1.paid = user_1.price
                        user_1.reminder = True
                        user_1.toll = ""
                        user_1.cash = False
                        user_1.pending = False
                        user_1.notice = user.notice
                        user_1.save()
                    except IndexError:
                        pass  

                # 왕복 픽업 없는 경우
                else:
                    full_price = original_price
                    if user.email1:
                        full_price += full_price * 0.1  # 편도 요금에 10% 추가

                    total_paid_text_full = f"===Gratitude=== Total Paid: ${int(full_price)}"

                    if not has_payment_record:
                        user.notice = (
                            f"{original_notice} | {total_paid_text_full}"
                            if original_notice else total_paid_text_full
                        )
                    else:
                        user.notice = original_notice

                    user.paid = full_price
                    user.reminder = True
                    user.toll = ""
                    user.cash = False
                    user.pending = False
                    user.save()

                    context.update({
                        'pickup_date': user.pickup_date,
                        'price': full_price,
                        'return_pickup_date': user.return_pickup_date if user else '',
                    })

            # multi payment 적용방식 
            if selected_option == "Gratitude For (M) Payment" and user:
                posts = Post.objects.filter(
                    Q(email__iexact=user.email),
                    pickup_date__gte=timezone.now().date()
                ).order_by('pickup_date')  # 가까운 날짜 순서로 정렬

                if posts.exists():
                    total_paid_applied = 0.0
                    updated_posts = []

                    # 폼에서 금액 가져오기
                    form_price_input = request.POST.get('adjustment_time')
                    try:
                        form_price = float(form_price_input) if form_price_input else None
                    except ValueError:
                        form_price = None

                    for post in posts:
                        post_price = float(post.price or 0)

                        if form_price is not None and form_price > 0:
                            # 폼 금액이 있는 경우 순차 적용
                            applied = min(post_price, form_price)
                            post.paid = applied
                            form_price -= applied
                        elif form_price is None:
                            # 폼 금액이 없는 경우: 예약 금액 그대로 적용
                            post.paid = post_price
                        else:
                            # 폼 금액 소진 후 남은 예약: paid = 0
                            post.paid = 0.0

                        total_paid_applied += post.paid

                        # 공통 필드 초기화
                        post.reminder = True
                        post.toll = ""
                        post.cash = False
                        post.pending = False
                        post.discount = ""

                        updated_posts.append(post)

                    # 메일에 표시할 결제 금액
                    if form_price_input:
                        paid_text = f"===(M) GRATITUDE=== Total Paid: ${form_price_input} (applied to upcoming bookings)"
                    else:
                        paid_text = f"===(M) GRATITUDE=== Total Paid: ${int(total_paid_applied)} ({len(updated_posts)} bookings)"

                    for post in updated_posts:
                        original_notice = (post.notice or "").strip()

                        has_payment_record = any(
                            keyword in original_notice 
                            for keyword in ["===STRIPE===", "===PAYPAL===", "===Gratitude===", "===(M) GRATITUDE==="]
                        )

                        if not has_payment_record:
                            post.notice = (
                                f"{original_notice} | {paid_text}"
                                if original_notice else paid_text
                            )

                        post.save()

                    context.update({
                        'price': int(total_paid_applied),
                    })

            
            if selected_option in ["Cancellation of Booking", "Cancellation by Client", "Apologies Cancellation of Booking"] and user:

                if user.return_pickup_time == "x":
                    user.cancelled = True
                    user.is_confirmed = False
                    user.pending = False
                    user.save()

                    second_user = Post.objects.filter(email__iexact=email)[1]
                    second_user.cancelled = True
                    second_user.is_confirmed = False
                    second_user.cash = False
                    second_user.pending = False
                    second_user.save()

                    context.update({
                        'booking_date': second_user.pickup_date,
                        'return_booking_date': second_user.return_pickup_date
                    })
                    
                else:
                    user.cancelled = True
                    user.save()
                    context.update({'booking_date': user.pickup_date, 'return_booking_date': None})                    
                    
            if selected_option == "Payment discrepancy" and user: 
                diff = round(float(user.price) - float(user.paid), 2)
                if diff > 0:
                    user.toll = "short payment"
                    context.update({'price': user.price, 'paid': user.paid, 'diff': f"{diff:.2f}"})
                    user.save()

            if selected_option == "Cash Payment Confirmed" and user: 
                
                if user.return_pickup_time == "x":
                    user.cash = True
                    user.reminder = True
                    user.pending = False
                    user.save()

                    second_user = Post.objects.filter(email__iexact=email)[1]                    
                    second_user.cash = True
                    second_user.reminder = True
                    second_user.pending = False
                    second_user.save()
                    
                else:
                    user.cash = True
                    user.reminder = True
                    user.pending = False
                    user.save()                       

            handle_email_sending(request, email, subject, template_name, context, user.email1)
              
        return render(request, 'basecamp/inquiry_done.html')  
    
    else:
        return render(request, 'basecamp/email_dispatch.html', {})
    

def paypal_ipn_error_email(subject, exception, item_name, payer_email, gross_amount):
    error_message = (
        f"Exception: {exception}\n"
        f"Payer Name: {item_name}\n"
        f"Payer Email: {payer_email}\n"
        f"Gross Amount: {gross_amount}"
    )
    send_mail(
        subject,
        error_message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.RECIPIENT_EMAIL],  
        fail_silently=False,
    )


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

def handle_checkout_session_completed(session):
    email = session.customer_details.email
    name = session.customer_details.name
    amount = session.amount_total / 100  # Amount is in cents
    payment_intent_id = session.payment_intent or session.id  # session.id로 대체 가능


    try:
        payment, created = StripePayment.objects.update_or_create(
            payment_intent_id=payment_intent_id,
            defaults={
                "name": name,
                "email": email,
                "amount": amount,
            }
        )
        print(f"StripePayment saved. created={created}")

    except Exception as e:
        stripe_payment_error_email(
            'Stripe Payment Save Error',
            str(e),
            name,
            email,
            amount
        )

def stripe_payment_error_email(subject, message, name, email, amount):
    content = f"""
    Subject: {subject}
    
    Error: {message}
    Name: {name}
    Email: {email}
    Amount: {amount}
    """

    send_mail(
        subject=subject,
        message=content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.RECIPIENT_EMAIL],
    )

@csrf_exempt
def recaptcha_verify(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        recaptcha_token = data.get('recaptchaToken')
        
        if not recaptcha_token:
            return JsonResponse({'success': False, 'message': 'No reCAPTCHA token provided'})

        # Verify the reCAPTCHA v3 token
        result = verify_recaptcha(recaptcha_token, version='v3')
        
        if result.get('success'):
            # The token is valid, handle your logic here
            return JsonResponse({'success': True})
        else:
            # The token is invalid
            return JsonResponse({'success': False, 'message': result.get('error-codes', 'Invalid reCAPTCHA token')})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


