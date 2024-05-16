from datetime import date, datetime, timedelta

import logging
import requests
import random

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt

from main.settings import RECIPIENT_EMAIL
from blog.models import Post, Inquiry, Payment, Driver, Inquiry_point, Inquiry_cruise
from blog.tasks import send_confirm_email


logger = logging.getLogger(__name__)


def index(request): return redirect('/home/')


def home(request): return render(request, 'basecamp/home.html')


def about_us(request): 
    return render(request, 'basecamp/about_us.html')


# Suburb names 
def artarmon(request): return render(
    request, 'basecamp/airport-transfers-artarmon.html')


def asquith(request): return render(
    request, 'basecamp/airport-transfers-asquith.html')


def berowra(request): return render(            
    request, 'basecamp/airport-transfers-berowra.html')


def blacktown(request): return render(
    request, 'basecamp/airport-transfers-blacktown.html')


def chatswood(request): return render(
    request, 'basecamp/airport-transfers-chatswood.html')


def doonside(request): return render(
    request, 'basecamp/airport-transfers-doonside.html')


def eastwood(request): return render(
    request, 'basecamp/airport-transfers-eastwood.html')


def epping(request): return render(
    request, 'basecamp/airport-transfers-epping.html')


def gordon(request): return render(
    request, 'basecamp/airport-transfers-gordon.html')


def hornsby(request): return render(
    request, 'basecamp/airport-transfers-hornsby.html')


def killara(request): return render(
    request, 'basecamp/airport-transfers-killara.html')


def lane_cove(request): return render(
    request, 'basecamp/airport-transfers-lane-cove.html')


def linfield(request): return render(
    request, 'basecamp/airport-transfers-linfield.html')


def macquarie_park(request): return render(
    request, 'basecamp/airport-transfers-macquarie-park.html')


def marsfield(request): return render(
    request, 'basecamp/airport-transfers-marsfield.html')


def middle_cove(request): return render(
    request, 'basecamp/airport-transfers-middle-cove.html')


def mini_bus(request): return render(
    request, 'basecamp/airport-transfers-mini-bus.html')


def mount_kuring_gai(request): return render(
    request, 'basecamp/airport-transfers-mount-kuring-gai.html')


def mt_colah(request): return render(
    request, 'basecamp/airport-transfers-mt-colah.html')


def north_shore(request): return render(
    request, 'basecamp/airport-transfers-north-shore.html')


def north_west(request): return render(
    request, 'basecamp/airport-transfers-north-west.html')


def normanhurst(request): return render(
    request, 'basecamp/airport-transfers-normanhurst.html')


def parramatta(request): return render(
    request, 'basecamp/airport-transfers-parramatta.html')


def pennant_hills(request): return render(
    request, 'basecamp/airport-transfers-pennant-hills.html')


def pymble(request): return render(
    request, 'basecamp/airport-transfers-pymble.html')


def roseville(request): return render(
    request, 'basecamp/airport-transfers-roseville.html')


def ryde(request): return render(
    request, 'basecamp/airport-transfers-ryde.html')


def st_ives(request): return render(
    request, 'basecamp/airport-transfers-st-ives.html')


def sydney_city(request): return render(
    request, 'basecamp/airport-transfers-sydney-city.html')


def thornleigh(request): return render(
    request, 'basecamp/airport-transfers-thornleigh.html')


def toongabbie(request): return render(
    request, 'basecamp/airport-transfers-toongabbie.html')


def turramurra(request): return render(
    request, 'basecamp/airport-transfers-turramurra.html')


def waitara(request): return render(
    request, 'basecamp/airport-transfers-waitara.html')


def wahroonga(request): return render(
    request, 'basecamp/airport-transfers-wahroonga.html')


def warrawee(request): return render(
    request, 'basecamp/airport-transfers-warrawee.html')


def west_pymble(request): return render(
    request, 'basecamp/airport-transfers-west-pymble.html')


def westleigh(request): return render(
    request, 'basecamp/airport-transfers-westleigh.html')


def willoughby(request): return render(
    request, 'basecamp/airport-transfers-willoughby.html')
    

def booking(request): 
    context = {
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
    }
    return render(request, 'basecamp/booking.html', context)


def booking_form(request): 
    context = {
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
    }
    return render(request, 'basecamp/booking_form.html', context)


@login_required
def confirmation(request): 
    return render(request, 'basecamp/confirmation.html')


def confirm_booking(request): 
    return render(request, 'basecamp/confirm_booking.html')


def cruise_booking(request): 
    context = {
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
    }
    return render(request, 'basecamp/cruise_booking.html', context)


def cruise_inquiry(request): 
    context = {
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
    }
    return render(request, 'basecamp/cruise_inquiry.html', context)


def cruise_inquiry_1(request): 
    return render(request, 'basecamp/cruise_inquiry_1.html')


def date_error(request): 
    return render(request, 'basecamp/date_error.html')


def flight_date_error(request): 
    return render(request, 'basecamp/flight_date_error.html')


def gen_lotto(request): 
    return render(request, 'basecamp/gen_lotto.html')


def gen_lotto_details(request): 
    return render(request, 'basecamp/gen_lotto_details.html')


def inquiry(request): 
    context = {
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
    }
    return render(request, 'basecamp/inquiry.html', context)


def inquiry1(request): 
    return render(request, 'basecamp/inquiry1.html')


def inquiry2(request): 
    context = {
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
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


def payonline(request): 
    return render(request, 'basecamp/payonline.html')


def paypal_notice(request): 
    return render(request, 'basecamp/paypal_notice.html')


def pickup_adjustment(request): 
    return render(request, 'basecamp/pickup_adjustment.html')


def pickup_adjustment_detail(request): 
    return render(request, 'basecamp/pickup_adjustment_detail.html')


def p2p(request): 
    context = {
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
    }
    return render(request, 'basecamp/p2p.html', context)


def p2p_booking(request):     
    return render(request, 'basecamp/p2p_booking.html')


def p2p_single(request): 
    context = {
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
    }
    return render(request, 'basecamp/p2p_single.html', context)


def privacy(request): 
    return render(request, 'basecamp/privacy.html')


def reminder(request): 
    return render(request, 'basecamp/reminder.html')


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


def sending_responses(request): 
    return render(request, 'basecamp/sending_responses.html')


def server_error(request): 
    return render(request, 'basecamp/500.html')


def server_error(request): 
    return render(request, 'basecamp/501.html')


def server_error(request): 
    return render(request, 'basecamp/502.html')


def server_error(request): 
    return render(request, 'basecamp/503.html')


def server_error(request): 
    return render(request, 'basecamp/504.html')


def server_error(request): 
    return render(request, 'basecamp/505.html')


def server_error(request): 
    return render(request, 'basecamp/506.html')


def server_error(request): 
    return render(request, 'basecamp/507.html')


def service(request): 
    return render(request, 'basecamp/service.html')


def sitemap(request): 
    return render(request, 'basecamp/sitemap.xml')


def soyoung(request): 
    return render(request, 'basecamp/soyoung.html')


def terms(request): 
    return render(request, 'basecamp/terms.html')


def yoosung(request): 
    return render(request, 'basecamp/yoosung.html')



def verify_recaptcha(response):
    data = {
        'secret': settings.RECAPTCHA_SECRET_KEY,
        'response': response
    }
    r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
    return r.json()


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


# Inquiry for airport 
def inquiry_details(request):
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        return_direction = request.POST.get('return_direction')
        return_flight_date = request.POST.get('return_flight_date')
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
            'flight_date': flight_date,
            'flight_number': flight_number,
            'pickup_time': pickup_time,
            'direction': direction,
            'street': street,
            'suburb': suburb,
            'no_of_passenger': no_of_passenger,
            'return_flight_date': return_flight_date,
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
            ''' .format(data['name'], data['contact'], data['email'],  data['flight_date'], data['flight_number'],
                        data['pickup_time'], data['direction'], data['street'],  data['suburb'], data['no_of_passenger'], 
                        data['return_flight_date'], data['return_flight_number'],data['return_pickup_time'])
            
            send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])

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
            ''' .format(data['name'], data['contact'], data['email'],  data['flight_date'], data['flight_number'],
                        data['pickup_time'], data['direction'], data['street'],  data['suburb'], data['no_of_passenger'], 
                        data['return_flight_date'], data['return_flight_number'],data['return_pickup_time'])
            
            send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL]) 
            
        p = Inquiry(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time ,message=message)
        
        p.save()
        
        today = date.today()
        if flight_date <= str(today):                      
            return render(request, 'basecamp/flight_date_error.html')   

        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})        
        else:
            return render(request, 'basecamp/inquiry_done.html')
        
    else:
        return render(request, 'basecamp/inquiry.html', {})


# inquiry for airport from home page
def inquiry_details1(request):
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        return_direction = request.POST.get('return_direction')
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
        return_pickup_time = request.POST.get('return_pickup_time')
        message = request.POST.get('message')
        
        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'flight_date': flight_date,
            'flight_number': flight_number,
            'pickup_time': pickup_time,
            'direction': direction,
            'street': street,
            'suburb': suburb,
            'no_of_passenger': no_of_passenger,
            'return_flight_date': return_flight_date,
            'return_flight_number': return_flight_number,
            'return_pickup_time': return_pickup_time
            }
     
        inquiry_email_exists = Inquiry.objects.filter(email=email).exists()
        post_email_exists = Post.objects.filter(email=email).exists()

        if inquiry_email_exists or post_email_exists:
            content = '''
            Hello, {} \n
            Exist in Inquiry or Post \n 
            *** From Home Page ***
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
            ''' .format(data['name'], data['contact'], data['email'],  data['flight_date'], data['flight_number'],
                        data['pickup_time'], data['direction'], data['street'],  data['suburb'], data['no_of_passenger'], 
                        data['return_flight_date'], data['return_flight_number'],data['return_pickup_time'])
            
            send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])

        else:
            content = '''
            Hello, {} \n
            Neither in Inquiry & Post \n 
            *** From Home Page ***
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
            ''' .format(data['name'], data['contact'], data['email'],  data['flight_date'], data['flight_number'],
                        data['pickup_time'], data['direction'], data['street'],  data['suburb'], data['no_of_passenger'], 
                        data['return_flight_date'], data['return_flight_number'],data['return_pickup_time'])
            
            send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])     
        
        p = Inquiry(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, 
                 return_flight_time=return_flight_time, return_pickup_time=return_pickup_time ,message=message)
        
        p.save() 

        return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/inquiry1.html', {})
    

# client to fill out the inquiry form
def booking_form_detail(request):
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        return_direction = request.POST.get('return_direction')
        return_flight_date = request.POST.get('return_flight_date')
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
            'flight_date': flight_date,
            'flight_number': flight_number,
            'pickup_time': pickup_time,
            'direction': direction,
            'street': street,
            'suburb': suburb,
            'no_of_passenger': no_of_passenger,
            'return_flight_date': return_flight_date,
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
            ''' .format(data['name'], data['contact'], data['email'],  data['flight_date'], data['flight_number'],
                        data['pickup_time'], data['direction'], data['street'],  data['suburb'], data['no_of_passenger'], 
                        data['return_flight_date'], data['return_flight_number'],data['return_pickup_time'])
            
            send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])

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
            ''' .format(data['name'], data['contact'], data['email'],  data['flight_date'], data['flight_number'],
                        data['pickup_time'], data['direction'], data['street'],  data['suburb'], data['no_of_passenger'], 
                        data['return_flight_date'], data['return_flight_number'],data['return_pickup_time'])
            
            send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])              

        
        p = Inquiry(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time ,message=message)
        
        p.save()


        today = date.today()
        if flight_date <= str(today):            
            if is_ajax(request):                
                return render(request, 'basecamp/flight_date_error.html')
            else:                
                return render(request, 'basecamp/flight_date_error.html')  

        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
        else:
            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/booking_form.html', {})


# Contact form
def inquiry_details2(request):
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email') 
        flight_date = request.POST.get('flight_date')      
        message = request.POST.get('message')     
        

        recaptcha_response = request.POST.get('g-recaptcha-response')
        result = verify_recaptcha(recaptcha_response)
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': 'Invalid reCAPTCHA. Please try the checkbox again.'}) 
           

        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'flight_date': flight_date,
            'message': message}
        
        today = date.today()
        if flight_date != str(today):
            if is_ajax(request):
                return render(request, 'basecamp/501.html')
            else:
                return render(request, 'basecamp/501.html')
                     
        message = '''
                Contact Form
                =====================
                name: {}
                contact: {}        
                email: {}
                flight date: {}
                message: {}              
                '''.format(data['name'], data['contact'], data['flight_date'],
                           data['email'], data['message'])
                
        send_mail(data['name'], message, '', [RECIPIENT_EMAIL])         
        

        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
        else:
            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/inquiry2.html', {})
    
    
# single point to point inquiry
def p2p_single_detail(request):    
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')
        pickup_time = request.POST.get('pickup_time')
        flight_number = request.POST.get('flight_number')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')        
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_pickup_time = request.POST.get('return_pickup_time')
        message = request.POST.get('message') 

        recaptcha_response = request.POST.get('g-recaptcha-response')
        result = verify_recaptcha(recaptcha_response)
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': 'Invalid reCAPTCHA. Please try the checkbox again.'}) 
               
        data = {
            'name': name,
            'email': email,
            'flight_date': flight_date,
            'pickup_time': pickup_time,
            'flight_number': flight_number,
            'street': street,
            'return_pickup_time': return_pickup_time
            }
        
        content = '''
        Hello, {} \n
        Point to Point single 
        *** Inquiry_points ***\n
        https://easygoshuttle.com.au                   
        =============================            
        Email: {}  
        Pick up time: {}      
        Start point: {}            
        End point: {}  
        Return pickup time: {}          
        
        =============================\n        
        Best Regards,
        EasyGo Admin \n\n        
        ''' .format(data['name'], data['email'], data['pickup_time'], data['flight_number'], data['street'], data['return_pickup_time'])
        send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])

        cruise = True                           
        
        p = Inquiry_point(name=name, contact=contact, email=email, flight_date=flight_date, cruise=cruise,
                          pickup_time=pickup_time, flight_number=flight_number, street=street, no_of_passenger=no_of_passenger, 
                          no_of_baggage=no_of_baggage, return_flight_date=return_flight_date, 
                          return_flight_number=return_flight_number, return_pickup_time=return_pickup_time, message=message)
        
        p.save()         
        
        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
        
        else:
            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/p2p_single.html', {})
    

# cruise inquiry 
def cruise_inquiry_detail(request):    
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')
        pickup_time = request.POST.get('pickup_time')
        flight_number = request.POST.get('flight_number')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')        
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
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
            'flight_date': flight_date,
            'pickup_time': pickup_time,
            'flight_number': flight_number,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'return_flight_date': return_flight_date,
            'return_flight_number': return_flight_number,
            'return_pickup_time': return_pickup_time, 
            'message': message
            }
        
        content = '''
        Hello, {} \n
        Cruise Inquiry
        *** Inquiry_cruise ***\n
        https://easygoshuttle.com.au                   
        =============================            
        Email: {}  
        Contact: {}
        Pick up time: {}      
        Start point: {}            
        End point: {}  
        No of passenger: {}
        no_of_baggage: {}
        return_flight_date: {}
        return_flight_number: {}
        Return pickup time: {}     
        Message: {}     
        
        =============================\n        
        Best Regards,
        EasyGo Admin \n\n        
        ''' .format(data['name'], data['email'], data['contact'], data['pickup_time'], data['flight_number'], data['street'], 
                    data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_flight_number'],
                    data['return_pickup_time'], data['message'])
        send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])

        cruise = True                                   
        
        p = Inquiry_cruise(name=name, contact=contact, email=email, flight_date=flight_date, cruise=cruise,
                          pickup_time=pickup_time, flight_number=flight_number, street=street, no_of_passenger=no_of_passenger, 
                          no_of_baggage=no_of_baggage, return_flight_date=return_flight_date, 
                          return_flight_number=return_flight_number, return_pickup_time=return_pickup_time, message=message)
        
        p.save() 


        if is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})        
        else:
            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/cruise_inquiry.html', {})
    

# cruise from home page 
def cruise_inquiry_detail_1(request):    
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        direction = request.POST.get('direction')
        flight_date = request.POST.get('flight_date')
        pickup_time = request.POST.get('pickup_time')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        if not flight_time:
            flight_time = 'cruise'
        street = request.POST.get('street')
        if not street:
            street = '130 Argly St'
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        return_direction = request.POST.get('return_direction')        
        return_flight_date = request.POST.get('return_flight_date')
        if not return_flight_date:
            return_flight_date = date.today().strftime('%Y-%m-%d')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
        if not return_flight_time:
            return_flight_time = datetime.now().strftime('%H:%M')
        return_pickup_time = request.POST.get('return_pickup_time')
        message = request.POST.get('message')

        # suburb = 'The Rocks'
        cruise = True
               
        data = {
            'name': name,
            'email': email,
            'direction': direction,
            'flight_date': flight_date,
            'pickup_time': pickup_time,
            'flight_number': flight_number,
            'return_pickup_time': return_pickup_time
            }
        
        content = '''
        Hello, {} \n
        Cruise inquiry \n
        From Home page \n
        ***Inquiry_cruise***\n
        https://easygoshuttle.com.au                   
        =============================            
        Email: {}  
        Direction: {}
        Pick up time: {}      
        Start point: {}            
        Return pickup time: {}          
        
        =============================\n        
        Best Regards,
        EasyGo Admin \n\n        
        ''' .format(data['name'], data['email'], data['direction'], data['pickup_time'], data['flight_number'], data['return_pickup_time'])
        send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])                           
        
        p = Inquiry_cruise(name=name, contact=contact, email=email, direction=direction, flight_date=flight_date, flight_time=flight_time,
                          pickup_time=pickup_time, flight_number=flight_number, no_of_passenger=no_of_passenger, 
                          no_of_baggage=no_of_baggage, return_direction=return_direction, return_flight_date=return_flight_date, cruise=cruise,
                          return_flight_time=return_flight_time, return_flight_number=return_flight_number, return_pickup_time=return_pickup_time, message=message)
        
        p.save() 

        
        return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/cruise_inquiry.html', {})
    
    
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

        # p = Booking_p2p(p2p_name=p2p_name, p2p_phone=p2p_phone, p2p_email=p2p_email, p2p_date=p2p_date,
        #                 first_pickup_location=first_pickup_location, first_putime=first_putime,
        #                 first_dropoff_location=first_dropoff_location, second_pickup_location=second_pickup_location,
        #                 second_putime=second_putime, second_dropoff_location=second_dropoff_location, third_pickup_location=third_pickup_location,
        #                 third_putime=third_putime, third_dropoff_location=third_dropoff_location, fourth_pickup_location=fourth_pickup_location,
        #                 fourth_putime=fourth_putime, fourth_dropoff_location=fourth_dropoff_location, p2p_passengers=p2p_passengers,p2p_baggage=p2p_baggage,
        #                 p2p_message=p2p_message, price=price)

        # p.save()


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
        flight_date = request.POST.get('flight_date')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        no_of_passenger = request.POST.get('no_of_passenger')
        
        today = date.today()        
        if not flight_date or flight_date <= str(today):
            return render(request, 'basecamp/505.html')
        
        
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
        
        data = {
            'flight_date': flight_date,
            'direction': direction,
            'suburb': suburb,
            'no_of_passenger': no_of_passenger,

        }

        # message = '''
        #         =====================
        #         Someone checked price
        #         =====================
        #         Flight date: {}
        #         Direction: {}        
        #         Suburb: {}
        #         No of passenger: {}              
        #         '''.format(data['flight_date'], data['direction'],
        #                    data['suburb'], data['no_of_passenger'])
                
        # send_mail(data['flight_date'], message, '', [RECIPIENT_EMAIL])

        if direction == 'To/From Cruise Transfers':
            return render(request, 'basecamp/cruise_inquiry_1.html',
                          {'flight_date': flight_date, 'direction': direction, 
                           'no_of_passenger': no_of_passenger, 'suburb': suburb},
                          )

        else: 
            return render(request, 'basecamp/inquiry1.html',
                          {'flight_date': flight_date, 'direction': direction, 'suburb': suburb,
                           'no_of_passenger': no_of_passenger},
                          )

    else:
        return render(request, 'basecamp/inquiry1.html', {})


# Booking by myself 
def confirmation_detail(request):
    if request.method == "POST":
        company_name = request.POST.get('company_name')
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        email1 = request.POST.get('email1')
        flight_date = request.POST.get('flight_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        return_direction = request.POST.get('return_direction')
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
        return_pickup_time = request.POST.get('return_pickup_time')
        message = request.POST.get('message') 
        notice = request.POST.get('notice')       
        price = request.POST.get('price')
        paid = request.POST.get('paid')
        
        data = {            
            'name': name,
            'contact': contact,
            'email': email,            
            'flight_date': flight_date}       
        
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
            send_mail(data['flight_date'], content,
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
            send_mail(data['flight_date'], content,
                      '', [RECIPIENT_EMAIL])

        sam_driver = Driver.objects.get(driver_name="Sam") 

        p = Post(company_name=company_name, name=name, contact=contact, email=email, email1=email1, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, notice=notice, price=price, paid=paid, driver=sam_driver)
        
        p.save()

        rendering = render(request, 'basecamp/confirmation_detail.html',
                        {'name' : name, 'email': email, })  
        
        html_content = render_to_string("basecamp/html_email-confirmation.html",
                                    {'company_name': company_name, 'name': name, 'contact': contact, 'email': email, 'email1': email1, 'flight_date': flight_date, 'flight_number': flight_number,
                                     'flight_time': flight_time, 'pickup_time': pickup_time, 'return_direction': return_direction,'return_flight_date': return_flight_date, 
                                     'return_flight_number': return_flight_number, 'return_flight_time': return_flight_time, 'return_pickup_time': return_pickup_time,
                                     'direction': direction, 'street': street, 'suburb': suburb, 'no_of_passenger': no_of_passenger, 'no_of_baggage': no_of_baggage,
                                     'message': message, 'notice': notice , 'price': price, 'paid': paid })
        
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
        flight_date = request.POST.get('flight_date')
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
        return_flight_date = request.POST.get('return_flight_date')
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
            'flight_date': flight_date,
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
            Return_flight_time: {}         
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['return_flight_time'])
            send_mail(data['flight_date'], content,
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
            Return_flight_time: {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['return_flight_time'])
            send_mail(data['flight_date'], content,
                      '', [RECIPIENT_EMAIL])
            
        sam_driver = Driver.objects.get(driver_name="Sam") 

        p = Post(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction, price=price,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, message=message, driver=sam_driver, discount=discount)
        
        p.save()

        today = date.today()
        if flight_date <= str(today):
            if is_ajax(request):
                return render(request, 'basecamp/flight_date_error.html')
            else:
                return render(request, 'basecamp/flight_date_error.html') 

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
        flight_date = request.POST.get('flight_date')
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
        return_flight_date = request.POST.get('return_flight_date')
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
            'flight_date': flight_date,
            'pickup_time': pickup_time,
            'flight_number': flight_number,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'return_flight_date': return_flight_date,
            'return_flight_number': return_flight_number,
            'return_pickup_time': return_pickup_time, 
            'message': message}       
        
        cruise_email = Inquiry_cruise.objects.filter(email=email).exists()
        post_email = Post.objects.filter(email=email).exists()  

        if cruise_email or post_email:             
                        
            content = '''
            Hello, {} \n  
            [Cruise Booking by client] >> Put price & Send email\n
            Exit in Inquiry_cruise or Post *\n 
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
            return_flight_date: {}
            return_flight_number: {}
            Return pickup time: {}     
            Message: {}     

            =============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['email'], data['contact'], data['pickup_time'], data['flight_number'], data['street'], 
                        data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_flight_number'],
                        data['return_pickup_time'], data['message'])
            send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])
        
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
            return_flight_date: {}
            return_flight_number: {}
            Return pickup time: {}     
            Message: {}     
            
            =============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['email'], data['contact'], data['pickup_time'], data['flight_number'], data['street'], 
                        data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_flight_number'],
                        data['return_pickup_time'], data['message'])
            send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])
            
        sam_driver = Driver.objects.get(driver_name="Sam") 

        p = Post(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, street=street, price=price,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, suburb=suburb, cruise=cruise,  
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number,  
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
        is_confirmed_str = request.POST.get('is_confirmed')
        is_confirmed = is_confirmed_str == 'True'

        inquiry = Inquiry.objects.filter(email=email).first()
        inquiry_cruise = Inquiry_cruise.objects.filter(email=email).first()
        inquiry_point = Inquiry.objects.filter(email=email).first()

        user = None
        for obj in [inquiry, inquiry_cruise, inquiry_point]:
            if obj:
                if user is None or obj.created > user.created:
                    user = obj

        if not user:
            return render(request, 'basecamp/500.html')

        name = user.name            
        contact = user.contact
        company_name = user.company_name
        email1 = user.email1            
        flight_date = user.flight_date
        flight_number = user.flight_number
        flight_time = user.flight_time or 'cruise'
        pickup_time = user.pickup_time
        direction = user.direction
        suburb = user.suburb or 'The Rocks'
        street = user.street
        no_of_passenger = user.no_of_passenger
        no_of_baggage = user.no_of_baggage
        return_direction = user.return_direction
        return_flight_date = user.return_flight_date
        return_flight_number = user.return_flight_number
        return_flight_time = user.return_flight_time
        return_pickup_time = user.return_pickup_time 
        cruise = user.cruise          
        message = user.message
        notice = user.notice
        price = user.price
        paid = user.paid          
        
        data = {
        'name': name,
        'email': email,            
        'flight_date': flight_date,
        'return_flight_number': return_flight_number}                    
        
        send_confirm_email.delay(data['name'], data['email'], data['flight_date'], data['return_flight_number'])
            
        sam_driver = Driver.objects.get(driver_name="Sam")    
            
        p = Post(name=name, contact=contact, email=email, company_name=company_name, email1=email1, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street, cruise=cruise,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction, 
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, message=message, notice=notice, price=price, paid=paid, is_confirmed=is_confirmed, driver=sam_driver)
        
        p.save()    
                
        return render(request, 'basecamp/confirmation_detail.html',
                        {'name' : name, 'email': email, })
        
    else:
        return render(request, 'beasecamp/confirm_booking.html', {}) 

     
# sending confirmation email first one   
def sending_email_first_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')             
        user = Post.objects.filter(email=email).first() 

        user.sent_email = True
        user.save() 

        if user.cruise:
            html_content = render_to_string("basecamp/html_email-confirmation-cruise.html", 
                                        {'company_name': user.company_name, 'name': user.name, 'contact': user.contact, 'email': user.email, 'email1': user.email1,
                                         'flight_date': user.flight_date, 'flight_number': user.flight_number,
                                         'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                         'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                         'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                         'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date, 
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
                                             'flight_date': user.flight_date, 'flight_number': user.flight_number,
                                             'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                             'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                             'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                             'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date, 
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
                                         'flight_date': user.flight_date, 'flight_number': user.flight_number,
                                         'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                         'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                         'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                         'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date, 
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

        return render(request, 'basecamp/confirmation_detail.html',
                        {'name' : user.name, 'email': email}) 
    
    else:
        return render(request, 'beasecamp/sending_email_first.html', {})   
    

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
                                         'flight_date': user.flight_date, 'flight_number': user.flight_number,
                                         'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                         'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                         'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                         'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date, 
                                         'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                                         'return_pickup_time': user.return_pickup_time,'message': user.message, 'notice': user.notice, 
                                         'price': user.price, 'paid': user.paid})
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
                                             'flight_date': user.flight_date, 'flight_number': user.flight_number,
                                             'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                             'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                             'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                             'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date, 
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
                                         'flight_date': user.flight_date, 'flight_number': user.flight_number,
                                         'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                         'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                         'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                         'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date, 
                                         'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                                         'return_pickup_time': user.return_pickup_time,'message': user.message, 'notice': user.notice, 
                                         'price': user.price, 'paid': user.paid})
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
            
        return render(request, 'basecamp/confirmation_detail.html',
                        {'name' : user.name }) 
    
    else:
        return render(request, 'basecamp/sending_email_second.html', {})
    

def sending_email_input_data_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')   
        field = request.POST.get('field')        

        inquiry = Inquiry.objects.filter(email=email).first()
        inquiry_cruise = Inquiry_cruise.objects.filter(email=email).first()
        inquiry_point = Inquiry.objects.filter(email=email).first()
        post = Post.objects.filter(email=email).first()

        user = None
        for obj in [inquiry, inquiry_cruise, inquiry_point, post]:
            if obj:
                if user is None or obj.created > user.created:
                    user = obj

        if not user:
            return render(request, 'basecamp/500.html')

        else:
            html_content = render_to_string("basecamp/html_email-input-date.html", 
                                        {'name': user.name, 'contact': user.contact, 'email': user.email, 
                                         'flight_date': user.flight_date, 'flight_number': user.flight_number,
                                         'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                         'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                         'no_of_baggage': user.no_of_baggage, 'field': field, 
                                         'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date, 
                                         'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                                         'return_pickup_time': user.return_pickup_time,'message': user.message, 'notice': user.notice, 
                                         })
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "Checking details - EasyGo",
                text_content,
                '',
                [email, RECIPIENT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()


        return render(request, 'basecamp/confirmation_detail.html',
                        {'name' : user.name, 'email': email}) 
    
    else:
        return render(request, 'beasecamp/sending_email_first.html', {})   



def save_data_only_detail(request):     
    if request.method == "POST":
        company_name = request.POST.get('company_name')
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        email1 = request.POST.get('email1')
        flight_date = request.POST.get('flight_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        street = request.POST.get('street')
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        return_direction = request.POST.get('return_direction')
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
        return_pickup_time = request.POST.get('return_pickup_time')
        message = request.POST.get('message')        
        price = request.POST.get('price')
        paid = request.POST.get('paid')
     
        sam_driver = Driver.objects.get(driver_name="Sam") 
 
        p = Post(company_name=company_name, name=name, contact=contact, email=email, email1=email1, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, message=message, price=price, paid=paid, driver=sam_driver)
        
        p.save()                   
        
        return render(request, 'basecamp/confirmation_detail.html',{'name' : name, })
    
    else:
        return render(request, 'beasecamp/save_data_only.html', {})  


# For Return Trip 
def return_trip_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')       
        message = request.POST.get('message')
        price = request.POST.get('price')
        
        user = Post.objects.filter(Q(email__iexact=email)).first()    
        
        if not user:
            return render(request, 'basecamp/503.html')    
            
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
            'flight_date': flight_date}       
            
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
        send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])     
        
        sam_driver = Driver.objects.get(driver_name="Sam")  
                    
        p = Post(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, price=price, 
                 driver=sam_driver)
        
        p.save()

        rendering = render(request, 'basecamp/inquiry_done.html')    
        
        return rendering
    
    else:
        return render(request, 'beasecamp/return_trip.html', {})        


# send invoice to customer
def invoice_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        discount = request.POST.get('discount')
        notice = request.POST.get('notice')  
        
        user = Post.objects.filter(email=email).first()

        price_as_float = float(user.price)

        if user.paid: 
            float_paid = float(user.paid)
        else:
            float_paid = 0.0    
                
        with_gst = round(price_as_float * 0.10, 2)
        surcharge = round(price_as_float * 0.03, 2) 
        
        if discount: 
            float_discount = float(discount)
        else:
            float_discount = 0.0 
        
        if user.paid:
            total_price = (round(price_as_float + with_gst + surcharge, 2)) - float_discount
            balance = round(total_price - float_paid, 2) 
        else:
            total_price = (round(price_as_float + with_gst, 2)) - float_discount
            balance = round(total_price - float_paid, 2)

        today = date.today()           
        
        if user.return_pickup_time:
            user = Post.objects.filter(email=email)[1]
            html_content = render_to_string("basecamp/html_email-invoice.html",
                                        {'notice': notice, 'name': user.name, 'company_name': user.company_name, 'contact': user.contact, 'discount': discount,
                                         'email': user.email, 'direction': user.direction, 'flight_date': user.flight_date, 'invoice_date': today, 
                                         'flight_number': user.flight_number, 'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                         'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date,
                                         'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 'return_pickup_time': user.return_pickup_time,
                                         'street': user.street, 'suburb': user.suburb, 'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                         'price': user.price, 'with_gst': with_gst, 'surcharge': surcharge, 'total_price': total_price, 
                                         'balance': balance, 'paid': float_paid, 'message': user.message })

            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                "Tax Invoice - EasyGo",
                text_content,
                '',
                [email, user.email1]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
        else:              
            user = Post.objects.filter(email=email).first()        
            html_content = render_to_string("basecamp/html_email-invoice.html",
                                        {'notice': notice, 'name': user.name, 'company_name': user.company_name,'contact': user.contact, 'discount': discount,
                                         'email': user.email, 'direction': user.direction, 'flight_date': user.flight_date, 'invoice_date': today,
                                         'flight_number': user.flight_number, 'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                         'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date,
                                         'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 'return_pickup_time': user.return_pickup_time,
                                         'street': user.street, 'suburb': user.suburb, 'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                         'price': user.price, 'with_gst': with_gst, 'surcharge': surcharge, 'total_price': total_price, 
                                         'balance': balance, 'paid': float_paid, 'message': user.message })

            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                "Tax Invoice - EasyGo",
                text_content,
                '',
                [email, user.email1]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        return render(request, 'basecamp/inquiry_done.html')  
    
    else:
        return render(request, 'beasecamp/invoice.html', {})
    

def flight_date_detail(request):       
    if request.method == "POST":          
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')

        inquiry = Inquiry.objects.filter(email=email).first()
        post = Post.objects.filter(email=email).first()

        user = None
        for obj in [inquiry, post]:
            if obj:
                if user is None or obj.created > user.created:
                    user = obj
        
        if not user:
            return render(request, 'basecamp/502.html')

        name = user.name
        contact = user.contact
        flight_number = user.flight_number
        flight_time = user.flight_time
        pickup_time = user.pickup_time
        direction = user.direction
        suburb = user.suburb
        street = user.street
        no_of_passenger = user.no_of_passenger
        no_of_baggage = user.no_of_baggage
        return_direction = user.return_direction
        return_flight_date = user.return_flight_date
        return_flight_number = user.return_flight_number
        return_flight_time = user.return_flight_time
        return_pickup_time = user.return_pickup_time
        message = user.message                        
        
        data = {
        'name': name,
        'contact': contact,
        'email': email,
        'flight_date': flight_date}       
        
        content = '''
        {} 
        'The date' amended from data_error.html \n
        >> Go to the Inquiry or Inquiry_point or Post \n
        https://easygoshuttle.com.au \n  
        ===============================
        Contact: {}
        Email: {}              
        ===============================\n        
        Best Regards,
        EasyGo Admin \n\n        
        ''' .format(data['name'], data['contact'], data['email'])
        send_mail(data['flight_date'], content, '', [RECIPIENT_EMAIL])       
            
        if isinstance(user, Inquiry):
            p = Inquiry (name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                     flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                     no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                     return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                     return_pickup_time=return_pickup_time, message=message)

            p.save()              

        elif isinstance(user, Post):
            sam_driver = Driver.objects.get(driver_name="Sam") 
            p = Post (name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                     flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                     no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                     return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                     return_pickup_time=return_pickup_time, message=message, driver=sam_driver)

            p.save()                
                
        return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/flight_date_error.html', {})
    

def reminder_detail(request):
    if request.method == "POST":
        email = request.POST.get('email')
        reminder_str = request.POST.get('reminder')
        reminder = True if reminder_str == 'True' else False
        today = date.today()  
        today_date = datetime.strptime(str(today), '%Y-%m-%d').date()  
        user_queryset = Post.objects.filter(email=email)
        filtered_queryset = user_queryset.filter(Q(flight_date__gt=today_date)).order_by('flight_date')
        user = filtered_queryset.first()

        if not user:
            return render(request, 'basecamp/506.html')

        else:
            user.reminder = reminder
            user.save()
            # sending_reminder_email(user)
            

            return render(request, 'basecamp/inquiry_done.html')

    else:
        return render(request, 'basecamp/reminder.html', {}) 

    
# send pickup adjustment email to customer
def pickup_adjustment_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')        
        adjustment_time = request.POST.get('adjustment_time')
        selected_option = request.POST.get('selected_option')

        today = datetime.now()
        seven_days_later = today + timedelta(days=7)
        
        user = Post.objects.filter(email=email, flight_date__range=[today, seven_days_later]).first()

        if selected_option == 'Departure earlier pickup':
            user.pickup_time = adjustment_time
            user.save()

            html_content = render_to_string("basecamp/html_email-departure-early.html",
                                        {'name': user.name, 'adjustment_time': adjustment_time, })
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "Urgent notice - EasyGo",
                text_content,
                '',
                [email, RECIPIENT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        elif selected_option == 'Departure later pickup':    
            user.pickup_time = adjustment_time
            user.save()
    
            html_content = render_to_string("basecamp/html_email-departure-late.html",
                                        {'name': user.name, 'adjustment_time': adjustment_time, })
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "Urgent notice - EasyGo",
                text_content,
                '',
                [email, RECIPIENT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        elif selected_option == 'Arrival earlier than schedule':   
            user.pickup_time = adjustment_time
            user.save()
     
            html_content = render_to_string("basecamp/html_email-arrival-early.html",
                                        {'name': user.name, 'adjustment_time': adjustment_time, })
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "Urgent notice - EasyGo",
                text_content,
                '',
                [email, RECIPIENT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        elif selected_option == 'Arrival later than schedule':        
            user.pickup_time = adjustment_time
            user.save()

            html_content = render_to_string("basecamp/html_email-arrival-late.html",
                                        {'name': user.name, 'adjustment_time': adjustment_time, })
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "Urgent notice - EasyGo",
                text_content,
                '',
                [email, RECIPIENT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        elif selected_option == 'Just late notice':        
            html_content = render_to_string("basecamp/html_email-just-late-notice.html",
                                        {'name': user.name, 'adjustment_time': adjustment_time, })
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "Urgent notice - EasyGo",
                text_content,
                '',
                [email, RECIPIENT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()


        return render(request, 'basecamp/inquiry_done.html')  
    
    else:
        return render(request, 'beasecamp/pickup_adjustment.html', {})
    

# sending the response via email 
def sending_responses_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')   
        selected_option = request.POST.get('selected_option')        
        
        user = Post.objects.filter(email=email).first()        

        if selected_option == "Payment Method":                 
            html_content = render_to_string("basecamp/html_email-response-payment.html",
                                        {'name': user.name})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "Payment Method - EasyGo",
                text_content,
                '',
                [email, RECIPIENT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        if selected_option == "Inquiry Meeting Point":                 
            html_content = render_to_string("basecamp/html_email-response-meeting.html",
                                        {'name': user.name})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "Meeting Point - EasyGo",
                text_content,
                '',
                [email, RECIPIENT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        if selected_option == "Gratitude For Payment":                 
            html_content = render_to_string("basecamp/html_email-response-payment-received.html",
                                        {'name': user.name})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                "Payment Recevied - EasyGo",
                text_content,
                '',
                [email, RECIPIENT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        if selected_option == "html_email-today": 
            today = date.today()     
            user_today = Post.objects.filter(email=email, flight_date=today).first()
            driver_instance = user_today.driver  
            if driver_instance: 
                driver_name = driver_instance.driver_name
                driver_contact = driver_instance.driver_contact
                driver_plate = driver_instance.driver_plate
                driver_car = driver_instance.driver_car     

                html_content = render_to_string("basecamp/html_email-today.html", 
                                                {'name': user_today.name, 'pickup_time': user_today.pickup_time, 'meeting_point': user_today.meeting_point, 
                                                 'direction': user_today.direction, 'cash': user_today.cash, 
                                                 'driver_name': driver_name, 'driver_contact': driver_contact, 'driver_plate': driver_plate, 
                                                 'driver_car': driver_car, })
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives(
                    "Today notice - EasyGo",
                    text_content,
                    '',
                    [email, RECIPIENT_EMAIL]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()        

                return render(request, 'basecamp/inquiry_done.html')  
        
            else:
                message = "No booking today found for this client!"                
                return render(request, 'basecamp/inquiry_done.html', {'message': message})  
            
        return render(request, 'basecamp/inquiry_done.html') 
    
    else:
        return render(request, 'beasecamp/sending_responses.html', {})    
    

@csrf_exempt
def paypal_ipn(request):
    if request.method == 'POST':
        item_name = request.POST.get('item_name')
        payer_email = request.POST.get('payer_email')
        gross_amount = request.POST.get('mc_gross')
        txn_id = request.POST.get('txn_id')

        # Check if payment with the same transaction ID already exists
        if Payment.objects.filter(txn_id=txn_id).exists():
            return HttpResponse(status=200, content="Duplicate IPN Notification")
        
        p = Payment(item_name=item_name, payer_email=payer_email, gross_amount=gross_amount, txn_id=txn_id)

        try:
            p.save()      
            
        except Exception as e:
            return HttpResponse(status=500, content="Error processing PayPal IPN")

        # Forward the complete IPN message back to PayPal for verification
        ipn_data = request.POST.copy()
        ipn_data['cmd'] = '_notify-validate'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post('https://ipnpb.paypal.com/cgi-bin/webscr', data=ipn_data, headers=headers, verify=True)
            response_content = response.text.strip()
            
            if response.status_code == 200 and response_content == 'VERIFIED':
                return HttpResponse(status=200)
            else:
                return HttpResponse(status=500, content="Error processing PayPal IPN")

        except requests.exceptions.RequestException as e:
            return HttpResponse(status=500, content="Error processing PayPal IPN")

    return HttpResponse(status=400)



# lotto
def gen_lotto_details(request):
    if request.method == 'POST':
        n = int(request.POST.get('num_games'))    
        lotto_numbers = list(range(1, 46))

        games = []
        
        for _ in range(n):
            winner_numbers = random.sample(lotto_numbers, 6)
            winner_numbers.sort()            
            games.append(winner_numbers)
        
        return render(request, 'gen_lotto_details.html', {'games': games})
    else:
        return render(request, 'gen_lotto.html')
