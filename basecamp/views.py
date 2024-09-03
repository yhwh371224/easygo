from datetime import date

import logging
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

from main.settings import RECIPIENT_EMAIL
from blog.models import Post, Inquiry, PaypalPayment, StripePayment, Driver
from blog.tasks import send_confirm_email, send_email_task, send_notice_email
from blog.sms_utils import send_sms_message
from basecamp.area import get_suburbs
from basecamp.area_full import get_more_suburbs
from basecamp.area_home import get_home_suburbs


logger = logging.getLogger(__name__)


def index(request): return redirect('/home/')


def home(request):
    suburbs = get_suburbs()
    home_suburbs = get_home_suburbs()

    logger.debug(f"home_suburbs: {home_suburbs}") 
    
    fixed_items = [
        "Select your option",
        "Hotels In City",  
        "International Airport",
        "Domestic Airport",
        "WhiteBay cruise terminal",
        "Overseas cruise terminal"
    ]
    
    remaining_items = sorted([item for item in home_suburbs if item not in fixed_items])
    
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
    # send_notice_email.delay('information accessed', 'information accessed', RECIPIENT_EMAIL)
    return render(request, 'basecamp/information.html')


def invoice(request): 
    return render(request, 'basecamp/invoice.html')


def invoice_details(request): 
    return render(request, 'basecamp/invoice_details.html')


def meeting_point(request): 
    return render(request, 'basecamp/meeting_point.html')


def more_suburbs(request): 
    # send_notice_email.delay('suburbs accessed', 'A user accessed suburbs', RECIPIENT_EMAIL)
    more_suburbs = get_more_suburbs()
    return render(request, 'basecamp/more_suburbs.html', {'more_suburbs': more_suburbs})


def more_suburbs1(request): 
    # send_notice_email.delay('suburbs_1 accessed', 'A user accessed suburbs_1', RECIPIENT_EMAIL)
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


def p2p_single_1(request):     
    return render(request, 'basecamp/p2p_single_1.html')


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


def save_data_only(request): 
    return render(request, 'basecamp/save_data_only.html')


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
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        pickup_date = request.POST.get('pickup_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        return_direction = request.POST.get('return_direction')
        return_pickup_date = request.POST.get('return_pickup_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
        return_pickup_time = request.POST.get('return_pickup_time')
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
            'flight_number': flight_number,
            'pickup_time': pickup_time,
            'direction': direction,
            'street': street,
            'suburb': suburb,
            'no_of_passenger': no_of_passenger,
            'return_pickup_date': return_pickup_date,
            'return_flight_number': return_flight_number,
            'return_pickup_time': return_pickup_time
            }
     
        inquiry_email_exists = Inquiry.objects.filter(email=email).exists()
        post_email_exists = Post.objects.filter(email=email).exists()

        if inquiry_email_exists or post_email_exists:
            content = '''
            Hello, {} \n
            Exist in Inquiry or Post *\n 
            https://easygoshuttle.com.au
            =============================
            Contact: {}
            Email: {}  
            Flight date: {}
            Flight number: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Return flight date {}
            Return flight number {}
            Return pickup time: {}
            =============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'],  data['pickup_date'], data['flight_number'],
                        data['pickup_time'], data['direction'], data['street'],  data['suburb'], data['no_of_passenger'], 
                        data['return_pickup_date'], data['return_flight_number'],data['return_pickup_time'])
            
            send_mail(data['pickup_date'], content, '', [RECIPIENT_EMAIL])

        else:
            content = '''
            Hello, {} \n
            Neither in Inquiry & Post *\n 
            https://easygoshuttle.com.au
            =============================
            Contact: {}
            Email: {}  
            Flight date: {}
            Flight number: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Return flight date {}
            Return flight number {}
            Return pickup time: {}
            =============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'],  data['pickup_date'], data['flight_number'],
                        data['pickup_time'], data['direction'], data['street'],  data['suburb'], data['no_of_passenger'], 
                        data['return_pickup_date'], data['return_flight_number'],data['return_pickup_time'])
            
            send_mail(data['pickup_date'], content, '', [RECIPIENT_EMAIL]) 
            
        p = Inquiry(name=name, contact=contact, email=email, pickup_date=pickup_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_pickup_date=return_pickup_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time ,message=message)
        
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
        name = request.POST.get('name')        
        email = request.POST.get('email')
        pickup_date = request.POST.get('pickup_date')        
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')        
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        
        data = {
            'name': name,            
            'email': email,
            'pickup_date': pickup_date,            
            'pickup_time': pickup_time,
            'direction': direction,            
            'suburb': suburb,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,           
            }
     
        inquiry_email_exists = Inquiry.objects.filter(email=email).exists()
        post_email_exists = Post.objects.filter(email=email).exists()

        if inquiry_email_exists or post_email_exists:
            content = '''
            Hello, {} \n
            Exist in Inquiry or Post \n 
            *** From Home Page *** \n
            ====Simple One====
            =============================            
            Email: {}  
            Flight date: {}            
            Pickup time: {}
            Direction: {}            
            Suburb: {}
            Passenger: {}   
            Baggage: {}         
            =============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['email'],  data['pickup_date'], data['pickup_time'], 
                        data['direction'], data['suburb'], data['no_of_passenger'], data['no_of_baggage'])
            
            send_mail(data['pickup_date'], content, '', [RECIPIENT_EMAIL])

        else:
            content = '''
            Hello, {} \n
            Neither in Inquiry & Post \n 
            *** From Home Page ***
            ====Simple One====
            =============================
            Email: {}  
            Flight date: {}            
            Pickup time: {}
            Direction: {}            
            Suburb: {}
            Passenger: {}        
            Baggage: {} 
            =============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['email'],  data['pickup_date'], data['pickup_time'], 
                        data['direction'], data['suburb'], data['no_of_passenger'], data['no_of_baggage'])
            
            send_mail(data['pickup_date'], content, '', [RECIPIENT_EMAIL])     
        
        p = Inquiry(name=name, email=email, pickup_date=pickup_date, 
                 pickup_time=pickup_time, direction=direction, suburb=suburb, 
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage)
        
        p.save() 

        return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/inquiry1.html', {})


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
                     
        message = '''
                Contact Form
                =====================
                name: {}
                contact: {}        
                email: {}
                flight date: {}
                message: {}              
                '''.format(data['name'], data['contact'], data['pickup_date'],
                           data['email'], data['message'])
                
        send_mail(data['name'], message, '', [RECIPIENT_EMAIL])         
        

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
        

        html_content = render_to_string("basecamp/html_email-p2p.html", 
            {'p2p_name': p2p_name, 'p2p_phone': p2p_phone, 'p2p_email': p2p_email, 'p2p_date': p2p_date, 
            'first_pickup_location': first_pickup_location, 'first_putime': first_putime, 'first_dropoff_location': first_dropoff_location, 
            'second_pickup_location': second_pickup_location, 'second_putime': second_putime, 'second_dropoff_location': second_dropoff_location, 
            'third_pickup_location': third_pickup_location, 'third_putime': third_putime, 'third_dropoff_location': third_dropoff_location, 
            'fourth_pickup_location': fourth_pickup_location, 'fourth_putime': fourth_putime, 'fourth_dropoff_location': fourth_dropoff_location, 
            'p2p_passengers': p2p_passengers, 'p2p_baggage': p2p_baggage, 'p2p_message': p2p_message,
            })

        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Multiple points inquiry",
            text_content,
            '',
            [p2p_email, RECIPIENT_EMAIL]
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send()       
        
        
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

        html_content = render_to_string("basecamp/html_email-p2p-confirmation.html", 
            {'p2p_name': p2p_name, 'p2p_phone': p2p_phone, 'p2p_email': p2p_email, 'p2p_date': p2p_date, 
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
            })

        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Multiple points inquiry",
            text_content,
            '',
            [p2p_email, RECIPIENT_EMAIL]
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send()       
        
        
        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
        
        else:
            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/p2p.html', {})



def price_detail(request):
    if request.method == "POST":
        pickup_date = request.POST.get('pickup_date')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        no_of_passenger = request.POST.get('no_of_passenger')

        if direction == 'Select your option' or suburb == 'Select your option':
            return render(request, 'basecamp/home_error.html')
        
        today = date.today()        
        if not pickup_date or pickup_date <= str(today):
            return render(request, 'basecamp/home_error.html')    

        send_email_task.delay(pickup_date, direction, suburb, no_of_passenger)
        
        #sub = int(suburbs.get(suburb))
        #no_p = int(no_of_passenger)
#
        #def price_cal3():
        #    if 1 <= no_p < 10 and direction == 'Drop off to Domestic Airport':
        #        return sub + (no_p * 10) - 10
        #    elif 10 <= no_p <= 13 and direction == 'Drop off to Domestic Airport':
        #        return sub + (no_p * 10) + 10
#
        #    elif 1 <= no_p < 10 and direction == 'Drop off to Intl Airport':
        #        return sub + (no_p * 10) - 10
        #    elif 10 <= no_p <= 13 and direction == 'Drop off to Intl Airport':
        #        return sub + (no_p * 10) + 10
#
        #    elif 1 <= no_p < 10 and direction == 'Pickup from Domestic Airport':
        #        return sub + (no_p * 10) 
        #    elif 10 <= no_p <= 13 and direction == 'Pickup from Domestic Airport':
        #        return sub + (no_p * 10) + 10
#
        #    elif 1 <= no_p < 10 and direction == 'Pickup from Intl Airport':
        #        return sub + (no_p * 10) 
        #    else:
        #        return sub + (no_p * 10) + 10
#
        #price_cal3()
        #price = str(price_cal3())
        
        context = {
            'pickup_date': pickup_date,
            'direction': direction,
            'suburb': suburb,
            'no_of_passenger': no_of_passenger,  
        }

        return render(request, 'basecamp/inquiry1.html', context)

    else:
        return render(request, 'basecamp/home.html')


# Booking by myself 
def confirmation_detail(request):
    if request.method == "POST":
        company_name = request.POST.get('company_name')
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        email1 = request.POST.get('email1')
        pickup_date = request.POST.get('pickup_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        return_direction = request.POST.get('return_direction')
        return_pickup_date = request.POST.get('return_pickup_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
        return_pickup_time = request.POST.get('return_pickup_time')
        message = request.POST.get('message') 
        notice = request.POST.get('notice')       
        price = request.POST.get('price')
        paid = request.POST.get('paid')
        cash = request.POST.get('cash') == 'True'         
        
        data = {            
            'name': name,
            'contact': contact,
            'email': email,            
            'pickup_date': pickup_date}       
        
        inquiry_email = Inquiry.objects.filter(email=email).exists()
        post_email = Post.objects.filter(email=email).exists()  

        if inquiry_email or post_email:             
                        
            content = '''
            Hello, {} \n  
            [Confirmation] 
            Exist in Inquiry or Post *\n 
            ===============================
            Contact: {}
            Email: {}              
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'])
            send_mail(data['pickup_date'], content,
                      '', [RECIPIENT_EMAIL])   
        
        else:
            content = '''
            Hello, {} \n 
            [Confirmation]  
            Neither in Inquiry & Post *\n 
            ===============================
            Contact: {}
            Email: {}              
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'])
            send_mail(data['pickup_date'], content,
                      '', [RECIPIENT_EMAIL])

        sam_driver = Driver.objects.get(driver_name="Sam") 

        p = Post(company_name=company_name, name=name, contact=contact, email=email, email1=email1, pickup_date=pickup_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, return_direction=return_direction,
                 return_pickup_date=return_pickup_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, notice=notice, price=price, paid=paid, cash=cash, driver=sam_driver)
        
        p.save()

        rendering = render(request, 'basecamp/inquiry_done.html')   
        
        html_content = render_to_string("basecamp/html_email-confirmation.html",
                                    {'company_name': company_name, 'name': name, 'contact': contact, 'email': email, 'email1': email1, 'pickup_date': pickup_date, 'flight_number': flight_number,
                                     'flight_time': flight_time, 'pickup_time': pickup_time, 'return_direction': return_direction,'return_pickup_date': return_pickup_date, 
                                     'return_flight_number': return_flight_number, 'return_flight_time': return_flight_time, 'return_pickup_time': return_pickup_time,
                                     'direction': direction, 'street': street, 'suburb': suburb, 'no_of_passenger': no_of_passenger, 'no_of_baggage': no_of_baggage,
                                     'message': message, 'notice': notice , 'price': price, 'cash': cash, 'paid': paid })
        
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            "Booking confirmation - EasyGo",
            text_content,
            '',
            [email, RECIPIENT_EMAIL, email1]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return rendering

    else:
        return render(request, 'basecamp/confirmation.html', {})


# airport booking by client
def booking_detail(request):
    if request.method == "POST":        
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        pickup_date = request.POST.get('pickup_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        message = request.POST.get('message')
        return_direction = request.POST.get('return_direction')
        return_pickup_date = request.POST.get('return_pickup_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
        return_pickup_time = request.POST.get('return_pickup_time') 

        price = 'TBA' 
        discount = 'TBA'   

        recaptcha_response = request.POST.get('g-recaptcha-response')
        result = verify_recaptcha(recaptcha_response)
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': 'Invalid reCAPTCHA. Please try the checkbox again.'}) 
        
        data = {
            'name': name,
            'contact': contact,
            'email': email,            
            'pickup_date': pickup_date,
            'flight_number': flight_number,            
            'street': street, 
            'suburb': suburb,
            'no_of_passenger': no_of_passenger,
            'return_pickup_date': return_pickup_date,
            'return_flight_number': return_flight_number,
            'return_flight_time': return_flight_time}       
        
        inquiry_email = Inquiry.objects.filter(email=email).exists()
        post_email = Post.objects.filter(email=email).exists()  

        if inquiry_email or post_email:             
                        
            content = '''
            Hello, {} \n  
            [Booking by client] >> Sending email only!\n
            Exit in Inquiry or Post *\n 
            https://easygoshuttle.com.au/sending_email_first/ \n 
            https://easygoshuttle.com.au/sending_email_second/ \n            
            ===============================
            Contact: {}
            Email: {}  
            Flight number: {}
            Address: {}, {}
            No of Pax: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}         
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'], data['street'], 
                        data['suburb'], data['no_of_passenger'], data['return_pickup_date'], data['return_flight_number'],
                        data['return_flight_time'])
            send_mail(data['pickup_date'], content,
                      '', [RECIPIENT_EMAIL])
        
        else:
            content = '''
            Hello, {} \n  
            [Booking by client] >> Sending email only!\n
            Neither in Inquiry & Post *\n 
            https://easygoshuttle.com.au/sending_email_first/ \n  
            https://easygoshuttle.com.au/sending_email_second/ \n       
           ===============================
            Contact: {}
            Email: {}  
            Flight number: {}
            Address: {}, {}
            No of Pax: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}         
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
           ''' .format(data['name'], data['contact'], data['email'], data['flight_number'], data['street'], 
                        data['suburb'], data['no_of_passenger'], data['return_pickup_date'], data['return_flight_number'],
                        data['return_flight_time'])
            send_mail(data['pickup_date'], content,
                      '', [RECIPIENT_EMAIL])
            
        sam_driver = Driver.objects.get(driver_name="Sam") 

        p = Post(name=name, contact=contact, email=email, pickup_date=pickup_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction, price=price,
                 return_pickup_date=return_pickup_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, message=message, driver=sam_driver, discount=discount)
        
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
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        pickup_date = request.POST.get('pickup_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        if not flight_time:
            flight_time = "cruise"
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        street = request.POST.get('street')
        if not street:
            street = '130 Argly St'
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        message = request.POST.get('message')
        return_pickup_date = request.POST.get('return_pickup_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_pickup_time = request.POST.get('return_pickup_time')
        return_flight_time = 'cruise'
        suburb = 'The Rocks'
        cruise = True
        discount = 'TBA'
        price = 'TBA'    

        recaptcha_response = request.POST.get('g-recaptcha-response')
        result = verify_recaptcha(recaptcha_response)
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': 'Invalid reCAPTCHA. Please try the checkbox again.'}) 
        
        data = {
            'name': name,
            'contact': contact, 
            'email': email,
            'pickup_date': pickup_date,
            'pickup_time': pickup_time,
            'flight_number': flight_number,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'return_pickup_date': return_pickup_date,
            'return_flight_number': return_flight_number,
            'return_pickup_time': return_pickup_time, 
            'message': message}       
        
        cruise_email = Inquiry.objects.filter(email=email).exists()
        post_email = Post.objects.filter(email=email).exists()  

        if cruise_email or post_email:             
                        
            content = '''
            Hello, {} \n  
            [Cruise Booking by client] >> Put price & Send email\n
            Exit in Inquiry or Post *\n 
            https://easygoshuttle.com.au/sending_email_first/ \n 
            https://easygoshuttle.com.au/sending_email_second/ \n            
            ===============================
            Email: {}  
            Contact: {}
            Pick up time: {}      
            Start point: {}            
            End point: {}  
            No of passenger: {}
            no_of_baggage: {}
            return_pickup_date: {}
            return_flight_number: {}
            Return pickup time: {}     
            Message: {}     

            =============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['email'], data['contact'], data['pickup_time'], data['flight_number'], data['street'], 
                        data['no_of_passenger'], data['no_of_baggage'], data['return_pickup_date'], data['return_flight_number'],
                        data['return_pickup_time'], data['message'])
            send_mail(data['pickup_date'], content, '', [RECIPIENT_EMAIL])
        
        else:
            content = '''
            Hello, {} \n  
            [Cruise Booking by client] >> Put price & Send email \n
            Neither in Inquiry & Post *\n 
            https://easygoshuttle.com.au/sending_email_first/ \n  
            https://easygoshuttle.com.au/sending_email_second/ \n       
           ===============================
            Email: {}  
            Contact: {}
            Pick up time: {}      
            Start point: {}            
            End point: {}  
            No of passenger: {}
            no_of_baggage: {}
            return_pickup_date: {}
            return_flight_number: {}
            Return pickup time: {}     
            Message: {}     
            
            =============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['email'], data['contact'], data['pickup_time'], data['flight_number'], data['street'], 
                        data['no_of_passenger'], data['no_of_baggage'], data['return_pickup_date'], data['return_flight_number'],
                        data['return_pickup_time'], data['message'])
            send_mail(data['pickup_date'], content, '', [RECIPIENT_EMAIL])
            
        sam_driver = Driver.objects.get(driver_name="Sam") 

        p = Post(name=name, contact=contact, email=email, pickup_date=pickup_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, street=street, price=price,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, suburb=suburb, cruise=cruise,  
                 return_pickup_date=return_pickup_date, return_flight_number=return_flight_number,  
                 return_pickup_time=return_pickup_time, return_flight_time=return_flight_time,
                 message=message, driver=sam_driver, discount=discount)
        
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
        
        users = Inquiry.objects.filter(email=email)

        if users.exists() and 0 <= index < len(users):
            user = users[index]
        else:
            return render(request, 'basecamp/email_error_confirmbooking.html')

        name = user.name            
        contact = user.contact
        company_name = user.company_name
        email1 = user.email1            
        pickup_date = user.pickup_date
        flight_number = user.flight_number
        flight_time = user.flight_time 
        pickup_time = user.pickup_time
        direction = user.direction
        suburb = user.suburb 
        street = user.street
        no_of_passenger = user.no_of_passenger
        no_of_baggage = user.no_of_baggage
        return_direction = user.return_direction
        return_pickup_date = user.return_pickup_date
        return_flight_number = user.return_flight_number
        return_flight_time = user.return_flight_time
        return_pickup_time = user.return_pickup_time 
        cruise = user.cruise          
        message = user.message
        notice = user.notice
        price = user.price
        paid = user.paid 
        cash = user.cash         
        
        data = {
        'name': name,
        'email': email,            
        'pickup_date': pickup_date,
        'return_flight_number': return_flight_number}                    
        
        send_confirm_email.delay(data['name'], data['email'], data['pickup_date'], data['return_flight_number'])
            
        sam_driver = Driver.objects.get(driver_name="Sam")    
            
        p = Post(name=name, contact=contact, email=email, company_name=company_name, email1=email1, pickup_date=pickup_date, flight_number=flight_number,
                flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street, cruise=cruise, 
                no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction, 
                return_pickup_date=return_pickup_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                return_pickup_time=return_pickup_time, message=message, notice=notice, price=price, paid=paid, cash=cash, is_confirmed=is_confirmed, driver=sam_driver)
        
        p.save()    
                
        return render(request, 'basecamp/inquiry_done.html') 
        
    else:
        return render(request, 'basecamp/confirm_booking.html', {}) 

     
# sending confirmation email first one   
def sending_email_first_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        index = request.POST.get('index', '1')

        try:
            index = int(index) - 1  
        except ValueError:
            return HttpResponse("Invalid index value", status=400)  
        
        users = Post.objects.filter(email=email)        
        if users.exists() and 0 <= index < len(users):
            user = users[index]  

            user.sent_email = True
            user.save()

            if user.cruise:
                html_content = render_to_string("basecamp/html_email-confirmation-cruise.html", 
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

            if user.discount == 'TBA':
                if user.cancelled: 
                    html_content = render_to_string("basecamp/html_email-cancelled.html", 
                                                    {'name': user.name, 'email': user.email })
                    
                    text_content = strip_tags(html_content)
                    email = EmailMultiAlternatives(
                        "Booking confirmation - EasyGo",
                        text_content,
                        '',
                        [email, RECIPIENT_EMAIL]
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send()

                else: 
                    html_content = render_to_string("basecamp/html_email-confirmation-pending.html", 
                                                    {'company_name': user.company_name, 'name': user.name, 'contact': user.contact, 'email': user.email, 'email1': user.email1,
                                                     'pickup_date': user.pickup_date, 'flight_number': user.flight_number,
                                                     'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                                     'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                                     'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                                     'return_direction': user.return_direction, 'return_pickup_date': user.return_pickup_date, 
                                                     'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                                                     'return_pickup_time': user.return_pickup_time,'message': user.message, 'notice': user.notice, 
                                                     'price': user.price, 'paid': user.paid, })
                    
                    text_content = strip_tags(html_content)
                    email = EmailMultiAlternatives(
                        "Booking confirmation - EasyGo",
                        text_content,
                        '',
                        [email, RECIPIENT_EMAIL]
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send()
                    
            else: 
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
                    [email, RECIPIENT_EMAIL, user.email1]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

            return render(request, 'basecamp/inquiry_done.html')  
        
        else:            
            return HttpResponse("No user found", status=400)

    else:
        return render(request, 'basecamp/sending_email_first.html', {})   
    

# sending confirmation email second one    
def sending_email_second_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')

        user = Post.objects.filter(email=email)[1]
        user1 = Post.objects.filter(email=email).first()    

        user.sent_email = True
        user.save()  

        if user.cruise:
            html_content = render_to_string("basecamp/html_email-confirmation-cruise.html",
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
                [email, RECIPIENT_EMAIL, user.email1]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        if user.discount == 'TBA':
            if user.cancelled: 
                html_content = render_to_string("basecamp/html_email-cancelled.html", 
                                            {'name': user.name, 'email': user.email })
                
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives(
                    "Booking confirmation - EasyGo",
                    text_content,
                    '',
                    [email, RECIPIENT_EMAIL]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

            else: 
                html_content = render_to_string("basecamp/html_email-confirmation-pending.html", 
                                            {'company_name': user.company_name, 'name': user.name, 'contact': user.contact, 'email': user.email, 'email1': user.email1,
                                             'pickup_date': user.pickup_date, 'flight_number': user.flight_number,
                                             'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                             'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                             'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                             'return_direction': user.return_direction, 'return_pickup_date': user.return_pickup_date, 
                                             'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                                             'return_pickup_time': user.return_pickup_time,'message': user.message, 'notice': user.notice, 
                                             'price': user.price, 'paid': user.paid})
                
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives(
                    "Booking confirmation - EasyGo",
                    text_content,
                    '',
                    [email, RECIPIENT_EMAIL]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

        else:
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
                [email, RECIPIENT_EMAIL, user.email1]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

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

        inquiry = Inquiry.objects.filter(email=email).first()
        post = Post.objects.filter(email=email).first()

        user = None
        for obj in [inquiry, post]:
            if obj:
                if user is None or obj.created > user.created:
                    user = obj

        if not user:
            return render(request, 'basecamp/400.html')

        else:
            html_content = render_to_string("basecamp/html_email-input-date.html", 
                                        {'name': user.name, 'contact': user.contact, 'email': user.email, 
                                         'pickup_date': user.pickup_date, 'flight_number': user.flight_number,
                                         'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                         'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                         'no_of_baggage': user.no_of_baggage, 'field': field, 
                                         'return_direction': user.return_direction, 'return_pickup_date': user.return_pickup_date, 
                                         'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                                         'return_pickup_time': user.return_pickup_time,'message': user.message, 'notice': user.notice, 
                                         })
            text_content = strip_tags(html_content)
            email_message = EmailMultiAlternatives(
                "Checking details - EasyGo",
                text_content,
                '',
                [email, RECIPIENT_EMAIL]
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()


        return render(request, 'basecamp/inquiry_done.html') 
    
    else:
        return render(request, 'basecamp/sending_email_first.html', {})   



def save_data_only_detail(request):     
    if request.method == "POST":
        company_name = request.POST.get('company_name')
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        email1 = request.POST.get('email1')
        pickup_date = request.POST.get('pickup_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        return_direction = request.POST.get('return_direction')
        return_pickup_date = request.POST.get('return_pickup_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
        return_pickup_time = request.POST.get('return_pickup_time')
        message = request.POST.get('message')        
        price = request.POST.get('price')
        paid = request.POST.get('paid')
     
        sam_driver = Driver.objects.get(driver_name="Sam") 
 
        p = Post(company_name=company_name, name=name, contact=contact, email=email, email1=email1, pickup_date=pickup_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_pickup_date=return_pickup_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, message=message, price=price, paid=paid, driver=sam_driver)
        
        p.save()                   
        
        return render(request, 'basecamp/inquiry_done.html')
    
    else:
        return render(request, 'basecamp/save_data_only.html', {})  


# For Return Trip 
def return_trip_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        pickup_date = request.POST.get('pickup_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')       
        message = request.POST.get('message')
        price = request.POST.get('price')
        
        user = Post.objects.filter(Q(email__iexact=email)).first()    
        
        if not user:
            return render(request, 'basecamp/403.html')    
            
        else:
            name = user.name
            contact = user.contact
            suburb = user.suburb
            street = user.street
            no_of_passenger = user.no_of_passenger
            no_of_baggage = user.no_of_baggage
            
        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'pickup_date': pickup_date}       
            
        content = '''
            {} 
            submitted the 'Return trip' \n
            sending first email only \n
            https://easygoshuttle.com.au/sending_email_first/ \n  
            https://easygoshuttle.com.au/sending_email_second/ \n
            ===============================
            Contact: {}
            Email: {}  
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'])
        send_mail(data['pickup_date'], content, '', [RECIPIENT_EMAIL])     
        
        sam_driver = Driver.objects.get(driver_name="Sam")  
                    
        p = Post(name=name, contact=contact, email=email, pickup_date=pickup_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, price=price, 
                 driver=sam_driver)
        
        p.save()

        rendering = render(request, 'basecamp/inquiry_done.html')    
        
        return rendering
    
    else:
        return render(request, 'basecamp/return_trip.html', {})        


# send invoice to customer
def invoice_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        surcharge = request.POST.get('surcharge')
        discount = request.POST.get('discount')
        inv_no = request.POST.get('inv_no')  
        toll = request.POST.get('toll')
        
        # users = Post.objects.filter(email=email)[:5]  
        if not inv_no:
            inv_no = 988390
        inv_no = int(inv_no)             
        today = date.today()

        # for user in users:
        user = Post.objects.filter(email=email).first()
        price_as_float = float(user.price)

        if user.paid: 
            float_paid = float(user.paid)
        else:
            float_paid = 0.0    
                
        with_gst = round(price_as_float * 0.10, 2)
        cal_surcharge = round(price_as_float * 0.03, 2)

        if surcharge: 
            float_surcharge = float(cal_surcharge)
        else:
            float_surcharge = 0.0 
        
        if discount: 
            float_discount = float(discount)
        else:
            if user.discount:
                float_discount = float(user.discount)
            else:
                float_discount = 0.0

        if toll: 
            float_toll = float(toll)
        else:
            float_toll = 0.0  
        
        if user.paid:
            total_price = (round(price_as_float + with_gst + float_surcharge + float_toll, 2)) - float_discount
            balance = round(total_price - float_paid, 2) 
        else:
            total_price = (round(price_as_float + with_gst + float_toll, 2)) - float_discount
            balance = round(total_price - float_paid, 2)

        if user.cash and user.paid:
            cash_balance = balance - (with_gst + float_surcharge)
            html_content = render_to_string("basecamp/html_email-invoice-cash.html",
                                        {'inv_no': inv_no, 'name': user.name, 'company_name': user.company_name,'contact': user.contact, 'discount': discount,
                                        'email': email, 'direction': user.direction, 'pickup_date': user.pickup_date, 'invoice_date': today,
                                        'flight_number': user.flight_number, 'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                        'return_direction': user.return_direction, 'return_pickup_date': user.return_pickup_date,
                                        'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 'return_pickup_time': user.return_pickup_time,
                                        'street': user.street, 'suburb': user.suburb, 'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                        'price': user.price, 'with_gst': with_gst, 'surcharge': float_surcharge, 'total_price': total_price, 'toll': toll, 
                                        'balance': cash_balance, 'paid': float_paid, 'message': user.message })
            text_content = strip_tags(html_content)

            recipient_list = [email, RECIPIENT_EMAIL]

            email = EmailMultiAlternatives(
                f"Tax Invoice #T{inv_no} - EasyGo",
                text_content,
                '',
                recipient_list
            )
            email.attach_alternative(html_content, "text/html")
            email.send()       
            
        elif user.return_pickup_time:
            user1 = Post.objects.filter(email=email)[1]
            html_content = render_to_string("basecamp/html_email-invoice.html",
                                        {'inv_no': inv_no, 'name': user.name, 'company_name': user1.company_name, 'contact': user1.contact, 'discount': discount,
                                        'email': user1.email, 'direction': user1.direction, 'pickup_date': user1.pickup_date, 'invoice_date': today, 
                                        'flight_number': user1.flight_number, 'flight_time': user1.flight_time, 'pickup_time': user1.pickup_time,
                                        'return_direction': user1.return_direction, 'return_pickup_date': user1.return_pickup_date,
                                        'return_flight_number': user1.return_flight_number, 'return_flight_time': user1.return_flight_time, 'return_pickup_time': user1.return_pickup_time,
                                        'street': user1.street, 'suburb': user1.suburb, 'no_of_passenger': user1.no_of_passenger, 'no_of_baggage': user1.no_of_baggage,
                                        'price': user1.price, 'with_gst': with_gst, 'surcharge': float_surcharge, 'total_price': total_price, 'toll': toll, 
                                        'balance': balance, 'paid': float_paid, 'message': user1.message })

            text_content = strip_tags(html_content)

            recipient_list = [email, RECIPIENT_EMAIL]

            email = EmailMultiAlternatives(
                f"Tax Invoice #T{inv_no} - EasyGo",
                text_content,
                '',
                recipient_list
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
        else:                    
            html_content = render_to_string("basecamp/html_email-invoice.html",
                                        {'inv_no': inv_no, 'name': user.name, 'company_name': user.company_name,'contact': user.contact, 'discount': discount,
                                        'email': email, 'direction': user.direction, 'pickup_date': user.pickup_date, 'invoice_date': today,
                                        'flight_number': user.flight_number, 'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                        'return_direction': user.return_direction, 'return_pickup_date': user.return_pickup_date,
                                        'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 'return_pickup_time': user.return_pickup_time,
                                        'street': user.street, 'suburb': user.suburb, 'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                        'price': user.price, 'with_gst': with_gst, 'surcharge': float_surcharge, 'total_price': total_price, 'toll': toll, 
                                        'balance': balance, 'paid': float_paid, 'message': user.message })

            text_content = strip_tags(html_content)

            recipient_list = [email, RECIPIENT_EMAIL]

            email = EmailMultiAlternatives(
                f"Tax Invoice #T{inv_no} - EasyGo",
                text_content,
                '',
                recipient_list
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            inv_no += 1  

        return render(request, 'basecamp/inquiry_done.html')  
    
    else:
        return render(request, 'basecamp/invoice.html', {})


# email_dispatch_detail 
def handle_email_sending(request, email, subject, template_name, context):
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    email_message = EmailMultiAlternatives(
        subject,
        text_content,
        '',
        [email, RECIPIENT_EMAIL]
    )
    email_message.attach_alternative(html_content, "text/html")
    email_message.send()

def email_dispatch_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')        
        adjustment_time = request.POST.get('adjustment_time')
        selected_option = request.POST.get('selected_option')
        
        user = Post.objects.filter(email=email).first()
        if not user:
            user = Inquiry.objects.filter(email=email).first()

        if adjustment_time and user:
            if user.return_pickup_time == 'x':
                user_1 = Post.objects.filter(email=email)[1]
                user_1.pickup_time = adjustment_time
                user_1.save() 
                send_sms_message(user_1.contact, "Your pickup time has been adjusted. Please check your email")
            else: 
                user.pickup_time = adjustment_time
                user.save()    
                send_sms_message(user_1.contact, "Your pickup time has been adjusted. Please check your email")    
        
        template_options = {
            'Earlier Pickup Requested for Departure': ("basecamp/html_email-departure-early.html", "Urgent notice - EasyGo"),
            'Later Pickup Requested for Departure': ("basecamp/html_email-departure-late.html", "Urgent notice - EasyGo"),
            'Early Arrival Notification': ("basecamp/html_email-arrival-early.html", "Urgent notice - EasyGo"),
            'Arrival Later Than Scheduled': ("basecamp/html_email-arrival-late.html", "Urgent notice - EasyGo"),
            'Notice of Delay': ("basecamp/html_email-just-late-notice.html", "Urgent notice - EasyGo"),
            'Adjusted Pickup Time': ("basecamp/html_email-just-adjustment.html", "Urgent notice - EasyGo"),
            "Payment Method": ("basecamp/html_email-response-payment.html", "Payment Method - EasyGo"),
            "Meeting Point Inquiry": ("basecamp/html_email-response-meeting.html", "Meeting Point - EasyGo"),
            "Gratitude For Payment": ("basecamp/html_email-response-payment-received.html", "Payment Received - EasyGo"),
            "Inquiry for further details": ("basecamp/html_email-response-more-details.html", "Inquiry for further details - EasyGo"),
            "Pickup Notice for Today": ("basecamp/html_email-today.html", "Pickup Notice for Today - EasyGo"),
            "Request for Driver Contact Information": ("basecamp/html_email-response-driver-contact.html", "For driver contact - EasyGo"),
            "Shared Ride Discount Offer": ("basecamp/html_email-shared-discount.html", "Discount notice - EasyGo"),
            "Cancellation of Booking": ("basecamp/html_email-response-cancel.html", "Cancellation of Booking: EasyGo"),
            "Apology emails": ("basecamp/html_email-response-apology-emails.html", "Apology emails: EasyGo"),
            "Payment discrepancy": ("basecamp/html_email-response-discrepancy.html", "Payment discrepancy: EasyGo")
        }

        if selected_option in template_options:
            template_name, subject = template_options[selected_option]
            context = {'email': email, 'name': user.name, 'adjustment_time': adjustment_time}

            if selected_option == "Pickup Notice for Today" and user:
                today = date.today()     
                user_today = Post.objects.filter(email=email, pickup_date=today).first()
                if user_today:
                    driver_instance = user_today.driver 
                    context.update({
                        'pickup_time': user_today.pickup_time, 'meeting_point': user_today.meeting_point, 
                        'direction': user_today.direction, 'cash': user_today.cash, 
                        'driver_name': driver_instance.driver_name, 'driver_contact': driver_instance.driver_contact, 
                        'driver_plate': driver_instance.driver_plate, 'driver_car': driver_instance.driver_car
                    })

            if selected_option == "Gratitude For Payment" and user:                     
                user.paid = float(user.price) + 0.10
                user.reminder = True
                user.save()
                if user.return_pickup_time == 'x':
                    user_1 = Post.objects.filter(email=email)[1]
                    user_1.paid = float(user.price) + 0.10
                    user_1.reminder = True
                    user_1.save() 
            
            if selected_option == "Cancellation of Booking" and user:                     
                user.cancelled = True
                user.save()

            if selected_option == "Payment discrepancy" and user: 
                diff = round(float(user.price) - float(user.paid), 2)
                context.update({'price': user.price, 'paid': user.paid, 'diff': diff})

            handle_email_sending(request, email, subject, template_name, context)
              
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
        # Invalid payload
        print('Error parsing payload: {}'.format(str(e)))
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print('Error verifying webhook signature: {}'.format(str(e)))
        return HttpResponse(status=400)

    # Handle the event
    if event.type == 'checkout.session.completed':
        session = event.data.object
        print('PaymentIntent was successful!')
        handle_checkout_session_completed(session)

    else:
        print('Unhandled event type {}'.format(event.type))

    return HttpResponse(status=200)

def handle_checkout_session_completed(session):
    email = session.customer_details.email
    name = session.customer_details.name
    amount = session.amount_total / 100  # Amount is in cents

    # Save payment information
    p = StripePayment(name=name, email=email, amount=amount)
    p.save()


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






