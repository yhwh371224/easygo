from django.shortcuts import render
from utils.email import send_text_email
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from main.settings import RECIPIENT_EMAIL
from blog.models import Post, Inquiry, Driver
from blog.tasks import send_confirm_email
from basecamp.area_home import get_home_suburbs
from basecamp.basecamp_utils import (
    is_ajax, parse_baggage, parse_date,
    to_bool, verify_turnstile,
    render_inquiry_done, booking_success_response, require_turnstile,
    is_duplicate_submission, parse_booking_dates, get_customer_status,
)


# airport booking by client
@require_turnstile
def booking_detail(request):
    if request.method == "POST":
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

        price = 'TBA'

        # ✅ 중복 제출 방지
        if is_duplicate_submission(Post, email):
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

        status_message, subject = get_customer_status(email, name, subject_prefix="[Client Booking] ")
        data['status_message'] = status_message

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

        content = email_content_template.format(**data)

        send_text_email(subject, content, [RECIPIENT_EMAIL])
            
        sam_driver = Driver.objects.get(driver_name="Sam") 

        # 🧳 개별 수하물 항목 수집
        baggage_str = parse_baggage(request)

        p = Post(name=name, contact=contact, email=email, pickup_date=pickup_date_obj, flight_number=flight_number, flight_time=flight_time, 
                 pickup_time=pickup_time, start_point=start_point, end_point=end_point, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=baggage_str, message=message, return_direction=return_direction, 
                 return_pickup_date=return_pickup_date_obj, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, return_start_point=return_start_point, return_end_point=return_end_point, driver=sam_driver,
                 price=price, )
        
        p.save()        
        
        return booking_success_response(request)

    else:
        return render(request, 'basecamp/booking/booking.html', {})


# cruise booking by client
@require_turnstile
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

        # ✅ 중복 제출 방지
        if is_duplicate_submission(Post, email):
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
            send_text_email(data['pickup_date'], content, [RECIPIENT_EMAIL])
        
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
            send_text_email(data['pickup_date'], content, [RECIPIENT_EMAIL])
            
        sam_driver = Driver.objects.get(driver_name="Sam")

        # 🧳 개별 수하물 항목 수집
        baggage_str = parse_baggage(request)         

        p = Post(name=name, contact=contact, email=email, pickup_date=pickup_date_obj, start_point=start_point,
                 end_point=end_point, pickup_time=pickup_time, price=price,
                 no_of_passenger=no_of_passenger, no_of_baggage=baggage_str,   
                 return_pickup_date=return_pickup_date_obj, return_start_point=return_start_point,  
                 return_pickup_time=return_pickup_time, return_end_point=return_end_point,
                 message=message, driver=sam_driver, )
        
        p.save()

        return booking_success_response(request)

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
            pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date, return_pickup_date)
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

        return render_inquiry_done(request)

    else:
        return render(request, 'basecamp/booking/confirm_booking.html', {})

# For Return Trip
@require_turnstile
def return_trip_detail(request):
    if request.method == "POST":
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
                pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date_str, return_pickup_date_str)
            except ValueError as e:
                return JsonResponse({'success': False, 'error': str(e)})

        # ✅ 중복 제출 방지
        if is_duplicate_submission(Post, email):
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

        send_text_email(subject, content, [RECIPIENT_EMAIL])
         
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