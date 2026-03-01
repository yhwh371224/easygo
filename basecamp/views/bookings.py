from datetime import date, timedelta
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from main.settings import RECIPIENT_EMAIL
from blog.models import Post, Inquiry, Driver
from blog.tasks import send_confirm_email
from basecamp.area import get_suburbs
from basecamp.area_home import get_home_suburbs
from basecamp.utils import (
    is_ajax, parse_date, handle_email_sending,
    add_bag, to_int, to_bool,
    verify_turnstile, get_sorted_suburbs
)


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
        # ✅ suburb 검증
        valid_suburbs = get_home_suburbs()
        if suburb not in valid_suburbs:
            return JsonResponse({'success': False, 'error': 'Invalid suburb selected.'})
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
        # ✅ suburb 검증
        valid_suburbs = get_home_suburbs()
        if suburb not in valid_suburbs:
            return JsonResponse({'success': False, 'error': 'Invalid suburb selected.'})
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

        return JsonResponse({'success': True, 'redirect_url': '/inquiry_done/'})
    
    else:
        return render(request, 'basecamp/booking/return_trip.html', {}) 