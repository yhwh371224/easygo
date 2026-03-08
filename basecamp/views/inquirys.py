from django.shortcuts import render, redirect
from utils.email import send_text_email
from django.db.models import Q
from django.http import JsonResponse
from main.settings import RECIPIENT_EMAIL
from blog.models import Post, Inquiry
from basecamp.area_home import get_home_suburbs
from basecamp.basecamp_utils import (
    is_ajax, parse_baggage, parse_date, handle_email_sending,
    verify_turnstile,
    render_inquiry_done, booking_success_response, require_turnstile,
    is_duplicate_submission, parse_booking_dates, get_customer_status,
)


# Inquiry for airport
@require_turnstile
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

        # ✅ 중복 제출 방지
        if is_duplicate_submission(Inquiry, email):
            return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})

        try:
            pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date_str, return_pickup_date_str)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})       

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
     
        status_message, _ = get_customer_status(email, name)
        data['status_message'] = status_message

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

        content = email_content_template.format(**data)        

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
        
        p.save()

        send_text_email(email_subject, content, [RECIPIENT_EMAIL])

        return booking_success_response(request)

    else:
        return render(request, 'basecamp/booking/inquiry.html', {})


# inquiry (simple one) for airport from home page
@require_turnstile
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
        if is_duplicate_submission(Inquiry, email):
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
     
        status_message, _ = get_customer_status(email, name)
        data['status_message'] = status_message

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

        content = email_content_template.format(**data)
        
        email_subject = f"Inquiry on {data['pickup_date']} - {data['name']}"
        send_text_email(email_subject, content, [RECIPIENT_EMAIL])

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
        baggage_str = parse_baggage(request)
        
        p = Inquiry(
            name=name, contact=contact, email=email, pickup_date=pickup_date_obj,  
            flight_number=flight_number, flight_time=flight_time, pickup_time=pickup_time, 
            direction=direction, suburb=suburb, street=street,
            start_point=start_point, end_point=end_point, 
            no_of_passenger=no_of_passenger, no_of_baggage=baggage_str, 
            message=message
        )
        
        p.save()

        return render_inquiry_done(request)

    else:
        return redirect('basecamp:home')
    

# Multiple points Inquiry
@require_turnstile
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