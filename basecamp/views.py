from django.shortcuts import render, redirect
from django.core.mail import send_mail
from basecamp.area import suburbs
from blog.models import Post, Inquiry, Payment
from basecamp.models import Inquiry_point
# from blog.tasks import send_email_delayed
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import date
#paypal ipn
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import logging
import requests


logger = logging.getLogger(__name__)


def index(request): return redirect('/home/')


def home(request): return render(request, 'basecamp/home.html')


def yoosung(request): return render(request, 'basecamp/yoosung.html')


def soyoung(request): return render(request, 'basecamp/soyoung.html')


def sitemap(request): return render(request, 'basecamp/sitemap.xml')


def booking_form(request): return render(request, 'basecamp/booking_form.html')


def booking(request): return render(request, 'basecamp/booking.html')


def confirmation(request): return render(request, 'basecamp/confirmation.html')


def confirm_booking(request): return render(request, 'basecamp/confirm_booking.html')


def return_flight_fields(request): return render(request, 'basecamp/return_flight_fields.html')


def return_trip(request): return render(request, 'basecamp/return_trip.html')


def return_trip_inquiry(request): return render(request, 'basecamp/return_trip_inquiry.html')


def sending_email_first(request): return render(request, 'basecamp/sending_email_first.html')


def sending_email_second(request): return render(request, 'basecamp/sending_email_second.html')


def save_data_only(request): return render(request, 'basecamp/save_data_only.html')


def inquiry(request): return render(request, 'basecamp/inquiry.html')


def inquiry1(request): return render(request, 'basecamp/inquiry1.html')


def inquiry2(request): return render(request, 'basecamp/inquiry2.html')


def inquiry2_detail(request): return render(request, 'basecamp/inquiry2_detail.html')


def invoice(request): return render(request, 'basecamp/invoice.html')


def invoice_details(request): return render(request, 'basecamp/invoice_details.html')


def about_us(request): return render(request, 'basecamp/about_us.html')


def privacy(request): return render(request, 'basecamp/privacy.html')


def information(request): return render(request, 'basecamp/information.html')


def service(request): return render(request, 'basecamp/service.html')


def terms(request): return render(request, 'basecamp/terms.html')


def payonline(request): return render(request, 'basecamp/payonline.html')


def paypal_notice(request): return render(request, 'basecamp/paypal_notice.html')


def meeting_point(request): return render(
    request, 'basecamp/meeting_point.html')


def sydney_city(request): return render(
    request, 'basecamp/airport-transfers-sydney-city.html')


def blacktown(request): return render(
    request, 'basecamp/airport-transfers-blacktown.html')


def chatswood(request): return render(
    request, 'basecamp/airport-transfers-chatswood.html')


def epping(request): return render(
    request, 'basecamp/airport-transfers-epping.html')


def hornsby(request): return render(
    request, 'basecamp/airport-transfers-hornsby.html')


def north_shore(request): return render(
    request, 'basecamp/airport-transfers-north-shore.html')


def north_west(request): return render(
    request, 'basecamp/airport-transfers-north-west.html')


def parramatta(request): return render(
    request, 'basecamp/airport-transfers-parramatta.html')


def ryde(request): return render(
    request, 'basecamp/airport-transfers-ryde.html')


def st_ives(request): return render(
    request, 'basecamp/airport-transfers-st-ives.html')


def thornleigh(request): return render(
    request, 'basecamp/airport-transfers-thornleigh.html')


def toongabbie(request): return render(
    request, 'basecamp/airport-transfers-toongabbie.html')


def westleigh(request): return render(
    request, 'basecamp/airport-transfers-westleigh.html')


def pennant_hills(request): return render(
    request, 'basecamp/airport-transfers-pennant-hills.html')


def normanhurst(request): return render(
    request, 'basecamp/airport-transfers-normanhurst.html')


def wahroonga(request): return render(
    request, 'basecamp/airport-transfers-wahroonga.html')


def asquith(request): return render(
    request, 'basecamp/airport-transfers-asquith.html')


def turramurra(request): return render(
    request, 'basecamp/airport-transfers-turramurra.html')


def waitara(request): return render(
    request, 'basecamp/airport-transfers-waitara.html')


def pymble(request): return render(
    request, 'basecamp/airport-transfers-pymble.html')


def gordon(request): return render(
    request, 'basecamp/airport-transfers-gordon.html')


def killara(request): return render(
    request, 'basecamp/airport-transfers-killara.html')


def berowra(request): return render(
    request, 'basecamp/airport-transfers-berowra.html')


def mt_colah(request): return render(
    request, 'basecamp/airport-transfers-mt-colah.html')


def mount_kuring_gai(request): return render(
    request, 'basecamp/airport-transfers-mount-kuring-gai.html')


def warrawee(request): return render(
    request, 'basecamp/airport-transfers-warrawee.html')


def lane_cove(request): return render(
    request, 'basecamp/airport-transfers-lane-cove.html')


def middle_cove(request): return render(
    request, 'basecamp/airport-transfers-middle-cove.html')


def west_pymble(request): return render(
    request, 'basecamp/airport-transfers-west-pymble.html')


def linfield(request): return render(
    request, 'basecamp/airport-transfers-linfield.html')


def marsfield(request): return render(
    request, 'basecamp/airport-transfers-marsfield.html')


def doonside(request): return render(
    request, 'basecamp/airport-transfers-doonside.html')


def eastwood(request): return render(
    request, 'basecamp/airport-transfers-eastwood.html')


def macquarie_park(request): return render(
    request, 'basecamp/airport-transfers-macquarie-park.html')


def mini_bus(request): return render(
    request, 'basecamp/airport-transfers-mini-bus.html')


def willoughby(request): return render(
    request, 'basecamp/airport-transfers-willoughby.html')


def server_error(request): return render(request, 'basecamp/500.html')


def server_error(request): return render(request, 'basecamp/501.html')


def server_error(request): return render(request, 'basecamp/502.html')


def server_error(request): return render(request, 'basecamp/503.html')


def server_error(request): return render(request, 'basecamp/504.html')


def server_error(request): return render(request, 'basecamp/505.html')


# Inquiry 
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
                                        
        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'flight_date': flight_date,
            'flight_number': flight_number,
            'flight_time': flight_time,
            'pickup_time': pickup_time,
            'direction': direction,
            'suburb': suburb,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'return_direction': return_direction,
            'return_flight_date': return_flight_date,
            'return_flight_number': return_flight_number,
            'return_flight_time': return_flight_time,
            'return_pickup_time': return_pickup_time,
            'message': message,}
     
        inquiry_email = Inquiry.objects.values_list('email', flat=True)
        post_email = Post.objects.values_list('email', flat=True)  
                     
        if (email in inquiry_email) and (email in post_email):            
            content = '''
            Hello, {} \n
            [Airport Inquiry]    
            * Both exist in Inquiry & Post *\n 
            https://easygoshuttle.com.au
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])
            
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif (email in inquiry_email) and not(email in post_email):            
            content = '''
            Hello, {} \n 
            [Airport Inquiry]   
            * Inquiry only exist *\n  
            https://easygoshuttle.com.au                    
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])
            
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif not(email in inquiry_email) and (email in post_email):            
            content = '''
            Hello, {} \n
            [Airport Inquiry]    
            * Post only exist *\n   
            https://easygoshuttle.com.au 
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])
            
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        else:
            content = '''
            Hello, {} \n 
            [Airport Inquiry]  
            * Neither in Inquiry & Post *\n
            https://easygoshuttle.com.au     
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])
            
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
        
        
        p = Inquiry(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time ,message=message)
        
        p.save()
        
        
        today = date.today()        
        if flight_date <= str(today):
            return render(request, 'basecamp/501.html')
                        
                            
        return render(request, 'basecamp/inquiry_details.html',
                        {'name' : name, 'email': email, }) 
                            
    else:
        return render(request, 'basecamp/inquiry.html', {})


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
            'flight_time': flight_time,
            'pickup_time': pickup_time,
            'direction': direction,
            'suburb': suburb,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'return_direction': return_direction,
            'return_flight_date': return_flight_date,
            'return_flight_number': return_flight_number,
            'return_flight_time': return_flight_time,
            'return_pickup_time': return_pickup_time,
            'message': message,}       
        
        inquiry_email = Inquiry.objects.values_list('email', flat=True)
        post_email = Post.objects.values_list('email', flat=True) 
                         
        if (email in post_email) and (email in inquiry_email):            
                        
            content = '''
            Hello, {} \n 
            [Quick Price] 
            * Both exist in Inquiry & Post *\n 
            https://easygoshuttle.com.au 
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])
            
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif (email in post_email) and not(email in inquiry_email):            
                        
            content = '''
            Hello, {} \n 
            [Quick Price] 
            * Post only exist *\n 
            https://easygoshuttle.com.au 
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])
            
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif not(email in post_email) and (email in inquiry_email):            
                        
            content = '''
            Hello, {} \n
            [Quick Price]  
            * Inquiry only exist *\n  
            https://easygoshuttle.com.au
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])
            
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
        
        else:
            content = '''
            Hello, {} \n
            [Quick Price]  
            * Neither in Inquiry & Post *\n   
            https://easygoshuttle.com.au
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])
            
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])        
        
        p = Inquiry(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, 
                 return_flight_time=return_flight_time, return_pickup_time=return_pickup_time ,message=message)
        
        p.save() 
        
        
        today = date.today()        
        if flight_date <= str(today):
            return render(request, 'basecamp/501.html')
               
                
        return render(request, 'basecamp/inquiry_details1.html',
                        {'name' : name, 'email': email, })

    else:
        return render(request, 'basecamp/inquiry1.html', {})
    

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
               
        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'flight_date': flight_date,
            'flight_number': flight_number,
            'flight_time': flight_time,
            'pickup_time': pickup_time,
            'direction': direction,
            'suburb': suburb,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'return_direction': return_direction,
            'return_flight_date': return_flight_date,
            'return_flight_number': return_flight_number,
            'return_flight_time': return_flight_time,
            'return_pickup_time': return_pickup_time,
            'message': message,           
        }
        
        inquiry_email = Inquiry.objects.values_list('email', flat=True) 
        post_email = Post.objects.values_list('email', flat=True)
                         
        if (email in inquiry_email) and (email in post_email):   
            content = '''
            Hello, {} \n
            [Inquiry from booking form] 
            * Both exist in Inquiry & Post *\n
            https://easygoshuttle.com.au                   
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])

            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif (email in inquiry_email) and not(email in post_email):   
            content = '''
            Hello, {} \n
            [Inquiry from booking form] 
            * Inquiry only exist *\n
            https://easygoshuttle.com.au
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])
            
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif not(email in inquiry_email) and (email in post_email):   
            content = '''
            Hello, {} \n
            [Inquiry from booking form] 
            * Post only exist *\n
            https://easygoshuttle.com.au
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])

            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        else:
            content = '''
            Hello, {} \n
            [Inquiry from booking form] 
            * Neither in Inquiry & Post *\n
            https://easygoshuttle.com.au
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Return direction: {}
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Return pickup time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_direction'],
                        data['return_flight_date'], data['return_flight_number'],
                        data['return_flight_time'], data['return_pickup_time'], data['message'])

            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
        
        p = Inquiry(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time ,message=message)
        
        p.save()
        
        
        today = date.today()        
        if flight_date <= str(today):
            return render(request, 'basecamp/501.html')
                   

        return render(request, 'basecamp/booking_form_detail.html',
                        {'name' : name, 'email': email, })
    
    else:
        return render(request, 'basecamp/booking_form.html', {})


# Contact 
def inquiry_details2(request):
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')        
        message = request.POST.get('message')     
        
        # html_content = render_to_string("basecamp/html_email-contact.html", 
        # {'name': name, 'contact': contact,
        # 'email': email, 'message': message, })
        
        # text_content = strip_tags(html_content)

        # email = EmailMultiAlternatives(
        #     "inquiry from contact_us",
        #     text_content,
        #     '',
        #     [email]
        # )
        
        # email.attach_alternative(html_content, "text/html")
        # email.send()
        
        return render(request, 'basecamp/inquiry2_detail.html',
                        {'name' : name})    
        
        
    else:
        return render(request, 'basecamp/inquiry2.html', {})
    
# single point to point    
def p2p_single(request):
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
            'message': message,           
        }
        
        inquiry_point_email = Inquiry_point.objects.values_list('email', flat=True) 
        post_email = Post.objects.values_list('email', flat=True)
                         
        if (email in inquiry_point_email) and (email in post_email):   
            content = '''
            Hello, {} \n
            [Inquiry from booking form] 
            * Both exist in Inquiry & Post *\n
            https://easygoshuttle.com.au                   
            ===============================
            Contact: {}
            Email: {}  
            Pick up time: {}      
            Start point: {}
            End point: {}
            Number of passenger: {}
            Number of baggage: {}
            Return date: {}
            Return pickup time: {}            
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['pickup_time'], data['flight_number'],
                        data['street'], data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_pickup_time'],
                        data['message'])

            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif (email in inquiry_point_email) and not(email in post_email):   
            content = '''
            Hello, {} \n
            [Inquiry from booking form] 
            * Inquiry only exist *\n
            https://easygoshuttle.com.au
            ===============================
            Contact: {}
            Email: {}  
            Pick up time: {}      
            Start point: {}
            End point: {}
            Number of passenger: {}
            Number of baggage: {}
            Return date: {}
            Return pickup time: {}            
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['pickup_time'], data['flight_number'],
                        data['street'], data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_pickup_time'],
                        data['message'])

            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif not(email in inquiry_point_email) and (email in post_email):   
            content = '''
            Hello, {} \n
            [Inquiry from booking form] 
            * Post only exist *\n
            https://easygoshuttle.com.au
            ===============================
            Contact: {}
            Email: {}  
            Pick up time: {}      
            Start point: {}
            End point: {}
            Number of passenger: {}
            Number of baggage: {}
            Return date: {}
            Return pickup time: {}            
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['pickup_time'], data['flight_number'],
                        data['street'], data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_pickup_time'],
                        data['message'])

            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        else:
            content = '''
            Hello, {} \n
            [Inquiry from booking form] 
            * Neither in Inquiry & Post *\n
            https://easygoshuttle.com.au
            ===============================
            Contact: {}
            Email: {}  
            Pick up time: {}      
            Start point: {}
            End point: {}
            Number of passenger: {}
            Number of baggage: {}
            Return date: {}
            Return pickup time: {}            
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['pickup_time'], data['flight_number'],
                        data['street'], data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_pickup_time'],
                        data['message'])

            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])        
        
        p = Inquiry_point(name=name, contact=contact, email=email, direction="Point to Point", flight_date=flight_date, flight_time="01:00", 
                          pickup_time=pickup_time, flight_number=flight_number, street=street, suburb="Cruise", no_of_passenger=no_of_passenger, 
                          no_of_baggage=no_of_baggage, return_direction="Point to Point", return_flight_date=return_flight_date, 
                          return_flight_time="01:00", return_flight_number=return_flight_number, return_pickup_time=return_pickup_time, message=message)
        
        p.save()        
        
        # today = date.today()        
        # if date <= str(today):
        #     return render(request, 'basecamp/501.html')                   

        return render(request, 'basecamp/p2p_single.html',
                        {'name' : name})           
    else:
        return render(request, 'basecamp/p2p_single.html', {})
    
    
# Multiple points
def p2p(request):
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

        html_content = render_to_string("basecamp/html_email-p2p-confirmation.html", 
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
            [p2p_email, 'info@easygoshuttle.com.au']
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return render(request, 'basecamp/p2p.html',
                        {'name' : p2p_name})    

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
                
        # send_mail(data['flight_date'], message, '', ['sungkam718@gmail.com'])

        return render(request, 'basecamp/inquiry1.html',
                      {'flight_date': flight_date, 'direction': direction, 'suburb': suburb,
                       'no_of_passenger': no_of_passenger},
                      )

    else:
        return render(request, 'basecamp/inquiry1.html', {})


# Post 
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
            'company_name': company_name,
            'name': name,
            'contact': contact,
            'email': email,
            'email1': email1,
            'flight_date': flight_date,
            'flight_number': flight_number,
            'flight_time': flight_time,
            'pickup_time': pickup_time,
            'direction': direction,
            'suburb': suburb,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'message': message,
            'price': price,
            }       
        
        post_email = Post.objects.values_list('email', flat=True)
        inquiry_email = Inquiry.objects.values_list('email', flat=True) 
                         
        if (email in post_email) and (email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
            [Confirmation] 
            * Both exist in Inquiry & Post *\n 
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {}
            price: {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['message'], data['price'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif (email in post_email) and not(email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
            [Confirmation] 
            * Post only exist *\n 
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {}
            price: {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['message'], data['price'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif not(email in post_email) and (email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
            [Confirmation] 
            * Inquiry only exist *\n 
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {}
            price: {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['message'], data['price'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
        
        else:
            content = '''
            Hello, {} \n 
            [Confirmation]  
            * Neither in Inquiry & Post *\n 
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {}
            price: {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['message'], data['price'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])

        p = Post(company_name=company_name, name=name, contact=contact, email=email, email1=email1, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, notice=notice, price=price, paid=paid, driver="Sam (0406783559)")
        
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
            [email, "info@easygoshuttle.com.au", email1]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        return rendering

    else:
        return render(request, 'basecamp/confirmation.html', {})


def booking_detail(request):
    if request.method == "POST":        
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        company_name = request.POST.get('company_name')
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
        message = request.POST.get('message')
        return_direction = request.POST.get('return_direction')
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
        return_pickup_time = request.POST.get('return_pickup_time')     
        price = request.POST.get('price')
        
        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'company_name': company_name,
            'email1': email1,
            'flight_date': flight_date,
            'flight_number': flight_number,
            'flight_time': flight_time,
            'pickup_time': pickup_time,
            'direction': direction,
            'suburb': suburb,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'message': message,
            'price': price,
            'return_flight_number': return_flight_number,
            }       
        
        post_email = Post.objects.values_list('email', flat=True)
        inquiry_email = Inquiry.objects.values_list('email', flat=True) 
                         
        if (email in post_email) and (email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
            [Booking by client] >> Sending email only!\n
            * Both in Inquiry & Post *\n 
            https://easygoshuttle.com.au/sending_email_first/ \n 
            https://easygoshuttle.com.au/sending_email_second/ \n            
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {}
            price {}
            return_flight_number {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['message'], data['price'], data['return_flight_number'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif (email in post_email) and not(email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
            [Booking by client] >> Sending email only!\n
            * Only in Post *\n 
            https://easygoshuttle.com.au/sending_email_first/ \n 
            https://easygoshuttle.com.au/sending_email_second/ \n      
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {}
            price {}
            return_flight_number {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['message'], data['price'], data['return_flight_number'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif not(email in post_email) and (email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
           [Booking by client] >> Sending email only!\n
            * Only in Inquiry *\n 
            https://easygoshuttle.com.au/sending_email_first/ \n 
            https://easygoshuttle.com.au/sending_email_second/ \n 
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {}
            price {}
            return_flight_number {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['message'], data['price'], data['return_flight_number'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
        
        else:
            content = '''
            Hello, {} \n  
            [Booking by client] >> Sending email only!\n
            * Neither in Inquiry & Post *\n 
            https://easygoshuttle.com.au/sending_email_first/ \n  
            https://easygoshuttle.com.au/sending_email_second/ \n       
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {}
            price {}
            return_flight_number {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['message'], data['price'], data['return_flight_number'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])

        p = Post(name=name, contact=contact, email=email, company_name=company_name, email1=email1, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, message=message, price=price, driver="Sam (0406783559)")
        
        p.save()
        
        # send_email_delayed.apply_async(args=[name, contact, email, flight_date, flight_number, flight_time,
        #                                       pickup_time, direction, suburb, street, no_of_passenger, no_of_baggage,
        #                                       message, price, is_confirmed], countdown=30)

        return render(request, 'basecamp/booking_detail.html',
                        {'name' : name, 'email': email, }) 

    else:
        return render(request, 'basecamp/booking.html', {})
    
    
def confirm_booking_detail(request):       
    if request.method == "POST":          
        email = request.POST.get('email')
        is_confirmed_str = request.POST.get('is_confirmed')
        is_confirmed = True if is_confirmed_str == 'True' else False
        user = (Inquiry.objects.filter(email=email).first()) or (Inquiry_point.objects.filter(email=email).first())
                            
        if not user:
            return render(request, 'basecamp/500.html') 
             
        else:
            name = user.name            
            contact = user.contact
            company_name = user.company_name
            email1 = user.email1            
            flight_date = user.flight_date
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
            notice = user.notice
            price = user.price
            paid = user.paid            
            
            data = {
            'name': name,
            'contact': contact,
            'email': email,
            'company_name': company_name,
            'email1': email1,
            'flight_date': flight_date,
            'flight_number': flight_number,
            'flight_time': flight_time,
            'pickup_time': pickup_time,
            'direction': direction,
            'suburb': suburb,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'message': message,
            'price': price,
            'return_flight_number': return_flight_number,
            }       
            
            content = '''
            {} 
            clicked the 'confirm booking' \n
            >> Sending email only! \n
            https://easygoshuttle.com.au/sending_email_first/ \n  
            https://easygoshuttle.com.au/sending_email_second/ \n
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {}    
            Price: {}
            Return flight no: {}        
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'], data['flight_time'], 
                        data['pickup_time'], data['direction'], data['street'], data['suburb'], data['no_of_passenger'], 
                        data['no_of_baggage'], data['message'], data['price'] , data['return_flight_number'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])       
            
        p = Post(name=name, contact=contact, email=email, company_name=company_name, email1=email1, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, message=message, notice=notice, price=price, paid=paid, is_confirmed=is_confirmed, driver="Sam (0406783559)")
        
        p.save()        
               
        # send_email_delayed.apply_async(args=[name, contact, email, flight_date, flight_number, flight_time,
        #                                       pickup_time, direction, suburb, street, no_of_passenger, no_of_baggage,
        #                                       message, price, is_confirmed], countdown=30)
                
        return render(request, 'basecamp/confirm_booking_detail.html',
                        {'name' : name, 'email': email, })
        
    else:
        return render(request, 'beasecamp/confirm_booking.html', {})      

     
# sending email first one   
def sending_email_first_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')             
        user = Post.objects.filter(email=email).first()  
                
        name = user.name
        
        html_content = render_to_string("basecamp/html_email-confirmation.html", #"basecamp/html_email-payment-success.html", 
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
            [email, "info@easygoshuttle.com.au"]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return render(request, 'basecamp/sending_email_first_detail.html',
                        {'name' : name, 'email': email}) 
    
    else:
        return render(request, 'beasecamp/sending_email_first.html', {})   
    

# sending email second one    
def sending_email_second_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        user = Post.objects.filter(email=email)[1]  
        
        if user:
            name = user.name
        
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
            [email, "info@easygoshuttle.com.au"]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return render(request, 'basecamp/sending_email_second_detail.html',
                        {'name' : name, 'email': email, }) 
    
    else:
        return render(request, 'beasecamp/sending_email_second.html', {})   


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
 
        p = Post(company_name=company_name, name=name, contact=contact, email=email, email1=email1, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, message=message, price=price, paid=paid, driver="Sam (0406783559)")
        
        p.save()                   
        
        return render(request, 'basecamp/save_data_only_detail.html',{'name' : name, })
    
    else:
        return render(request, 'beasecamp/save_data_only.html', {})  
    
    
# From Inquiry to Inquiry 



# From Inquiry to Inquiry return trip
def return_trip_inquiry_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')
        message = request.POST.get('message')        
        
        user = Inquiry.objects.filter(email=email).first()   
         
        if not user:
            return render(request, 'basecamp/504.html')  
             
        else:
            name = user.name
            contact = user.contact
            suburb = user.suburb
            street = user.street
            no_of_passenger = user.no_of_passenger
            no_of_baggage = user.no_of_baggage
            notice = user.notice
            price = user.price
            
        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'flight_date': flight_date,
            'flight_number': flight_number,
            'flight_time': flight_time,
            'pickup_time': pickup_time,
            'direction': direction,
            'suburb': suburb,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'message': message,
            'notice': notice,
            'price': price,
            }       
            
        content = '''
        {} 
        clicked the 'inquiry return trip' \n
        >> Sending inquiry email only! \n   
        https://easygoshuttle.com.au \n    
        ===============================
        Contact: {}
        Email: {}  
        Flight no: {}      
        Flight time: {}
        Pickup time: {}
        Direction: {}
        Street: {}
        Suburb: {}
        Passenger: {}
        Baggage: {}
        Messag
        {}  
        Notice: {}
        Price: {} \n          
        ===============================\n        
        Best Regards,
        EasyGo Admin \n\n        
        ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                    data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                    data['no_of_passenger'], data['no_of_baggage'], data['message'], data['notice'], data['price'])
        send_mail(data['flight_date'], content,
                  '', ['info@easygoshuttle.com.au'])       
            
        p = Inquiry(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, notice=notice, price=price)
        
        p.save()

        rendering = render(request, 'basecamp/retrieve_post_detail.html',
                        {'name' : name, 'email': email, })        

        html_content = render_to_string("basecamp/html_email-inquiry-response.html",
                                    {'name': name, 'contact': contact, 'email': email,
                                     'flight_date': flight_date, 'flight_number': flight_number,
                                     'flight_time': flight_time, 'pickup_time': pickup_time,
                                     'direction': direction, 'street': street, 'suburb': suburb,
                                     'no_of_passenger': no_of_passenger, 'no_of_baggage': no_of_baggage,
                                     'message': message, 'notice': notice, 'price': price })
    
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Booking inquiry - EasyGo",
            text_content,
            '',
            [email, 'info@easygoshuttle.com.au']
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return rendering
    
    else:
        return render(request, 'beasecamp/return_trip_inquiry.html', {})         


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
        
        user = Post.objects.filter(email=email).first()    
        
        if not user:
            return render(request, 'basecamp/503.html')    
            
        else:
            name = user.name
            contact = user.contact
            suburb = user.suburb
            street = user.street
            no_of_passenger = user.no_of_passenger
            no_of_baggage = user.no_of_baggage
            paid = user.paid
            notice = user.notice
            
        data = {
            'name': name,
            'contact': contact,
            'email': email,
            'flight_date': flight_date,
            'flight_number': flight_number,
            'flight_time': flight_time,
            'pickup_time': pickup_time,
            'direction': direction,
            'suburb': suburb,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'message': message,
            'price': price,
            'paid': paid,
            }       
            
        content = '''
            {} 
            submitted the 'Return trip' \n
            sending first email only \n
            https://easygoshuttle.com.au/sending_email_first/ \n  
            https://easygoshuttle.com.au/sending_email_second/ \n
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {} \n
            Price: {}           
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['message'], data['price'])
        send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])       
                    
        p = Post(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, notice=notice, price=price, 
                 paid=paid, driver="Sam (0406783559)")
        
        p.save()
        
        # send_email_delayed.apply_async(args=[name, contact, email, flight_date, flight_number, flight_time,
        #                                   pickup_time, direction, suburb, street, no_of_passenger, no_of_baggage,
        #                                   message, price, is_confirmed], countdown=300)

        rendering = render(request, 'basecamp/return_trip_detail.html',
                        {'name' : name, 'email': email, })    
        
        return rendering
    
    else:
        return render(request, 'beasecamp/return_trip.html', {})        


# send invoice to customer
def invoice_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        notice = request.POST.get('notice')  
        
        user = Post.objects.filter(email=email).first()        
        
        if user.return_pickup_time:
            user = Post.objects.filter(email=email)[1]
            html_content = render_to_string("basecamp/html_email-invoice.html",
                                        {'notice': notice, 'name': user.name, 'company_name': user.company_name, 'contact': user.contact, 
                                         'email': user.email, 'direction': user.direction, 'flight_date': user.flight_date, 
                                         'flight_number': user.flight_number, 'flight_time': user.flight_time, 
                                         'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date,
                                         'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                                         'street': user.street, 'suburb': user.suburb, 'no_of_passenger': user.no_of_passenger, 
                                         'price': user.price, 'paid': user.paid })

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
                                        {'notice': notice, 'name': user.name, 'contact': user.contact, 
                                         'email': user.email, 'direction': user.direction, 'flight_date': user.flight_date, 
                                         'flight_number': user.flight_number, 'flight_time': user.flight_time, 
                                         'return_direction': user.return_direction, 'return_flight_date': user.return_flight_date,
                                         'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                                         'street': user.street, 'suburb': user.suburb, 'no_of_passenger': user.no_of_passenger, 
                                         'price': user.price, 'paid': user.paid })

            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                "Tax Invoice - EasyGo",
                text_content,
                '',
                [email, user.email1]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        return render(request, 'basecamp/invoice_details.html', {})  
    
    else:
        return render(request, 'beasecamp/invoice.html', {})
    
    

def flight_date_detail(request):       
    if request.method == "POST":          
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')
        user = Inquiry.objects.filter(email=email).first() 
                            
        if not user:
            return render(request, 'basecamp/502.html')   
             
        else:
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
            'flight_date': flight_date,
            'flight_number': flight_number,
            'flight_time': flight_time,
            'pickup_time': pickup_time,
            'direction': direction,
            'suburb': suburb,
            'street': street,
            'no_of_passenger': no_of_passenger,
            'no_of_baggage': no_of_baggage,
            'message': message,
            
            }       
            
            content = '''
            {} 
            'flight date' amended from 501.html \n
            >> Go to the Inquiry database \n
            https://easygoshuttle.com.au \n  
            ===============================
            Contact: {}
            Email: {}  
            Flight no: {}      
            Flight time: {}
            Pickup time: {}
            Direction: {}
            Street: {}
            Suburb: {}
            Passenger: {}
            Baggage: {}
            Messag
            {}            
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['message'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])       
            
            
        p = Inquiry (name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_direction=return_direction,
                 return_flight_date=return_flight_date, return_flight_number=return_flight_number, return_flight_time=return_flight_time, 
                 return_pickup_time=return_pickup_time, message=message)
        
        p.save()        
        
                
        return render(request, 'basecamp/inquiry_details1.html',
                        {'name' : name, 'email': email, })

    else:
        return render(request, 'basecamp/inquiry1.html', {})
    
    

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

