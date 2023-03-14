from django.shortcuts import render, redirect
from django.core.mail import send_mail
from basecamp.area import suburbs
from blog.models import Post, Inquiry
from django.http import HttpResponseBadRequest
from blog.tasks import send_email_delayed
from django.http import JsonResponse

# html email required stuff
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def index(request): return redirect('/home/')


def home(request): return render(request, 'basecamp/home.html')


def sitemap(request): return render(request, 'basecamp/sitemap.xml')


def booking_form(request): return render(request, 'basecamp/booking_form.html')


def booking(request): return render(request, 'basecamp/booking.html')


def confirmation(request): return render(request, 'basecamp/confirmation.html')


def confirm_booking(request): return render(request, 'basecamp/confirm_booking.html')


def retrieve_inquiry(request): return render(request, 'basecamp/retrieve_inquiry.html')


def retrieve_post(request): return render(request, 'basecamp/retrieve_post.html')


def retrieve_inquiry_to_inquiry(request): return render(request, 'basecamp/retrieve_inquiry_to_inquiry.html')


def return_flight_fields(request): return render(request, 'basecamp/return_flight_fields.html')


def return_trip(request): return render(request, 'basecamp/return_trip.html')


def return_trip_inquiry(request): return render(request, 'basecamp/return_trip_inquiry.html')


def re_confirm(request): return render(request, 'basecamp/re_confirm.html')


def re_confirm_email(request): return render(request, 'basecamp/re_confirm_email.html')


def save_data_only(request): return render(request, 'basecamp/save_data_only.html')


def inquiry(request): return render(request, 'basecamp/inquiry.html')


def inquiry1(request): return render(request, 'basecamp/inquiry1.html')


def invoice(request): return render(request, 'basecamp/invoice.html')


def about_us(request): return render(request, 'basecamp/about_us.html')


def privacy(request): return render(request, 'basecamp/privacy.html')


def information(request): return render(request, 'basecamp/information.html')


def service(request): return render(request, 'basecamp/service.html')


def terms(request): return render(request, 'basecamp/terms.html')


def payonline(request): return render(request, 'basecamp/payonline.html')


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


def server_error(request): return render(
    request, 'basecamp/500.html')


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
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
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
            'return_flight_date': return_flight_date,
            'return_flight_number': return_flight_number,
            'return_flight_time': return_flight_time,
            'message': message,}
     
        inquiry_email = Inquiry.objects.values_list('email', flat=True)
        post_email = Post.objects.values_list('email', flat=True)  
                     
        if (email in inquiry_email) and (email in post_email):            
            content = '''
            Hello, {} \n   
            * Both exist in Inquiry & Post *\n     
            [Airport Inquiry]       
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
            Return flight date: {}
            Return flight no: {}
            Return flight time: {}
            Messag
            {}
            ===============================\n        
            Best Regards,
            EasyGo Admin \n\n        
            ''' .format(data['name'], data['contact'], data['email'], data['flight_number'],
                        data['flight_time'], data['pickup_time'], data['direction'], data['street'], data['suburb'],
                        data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_flight_number'],
                        data ['return_flight_time'], data['message'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif (email in inquiry_email) and not(email in post_email):            
            content = '''
            Hello, {} \n   
            * Inquiry only exist *\n     
            [Airport Inquiry]       
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
                        data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_flight_number'],
                        data ['return_flight_time'], data['message'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        elif not(email in inquiry_email) and (email in post_email):            
            content = '''
            Hello, {} \n   
            * Post only exist *\n   
            [Airport Inquiry]       
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
                        data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_flight_number'],
                        data ['return_flight_time'], data['message'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
            
        else:
            content = '''
            Hello, {} \n  
            * Neither in Inquiry & Post *\n     
            [Airport Inquiry]       
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
                        data['no_of_passenger'], data['no_of_baggage'], data['return_flight_date'], data['return_flight_number'],
                        data ['return_flight_time'], data['message'])
            send_mail(data['flight_date'], content,
                      '', ['info@easygoshuttle.com.au'])
        
        
        p = Inquiry(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_flight_date=return_flight_date,
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, message=message)
        p.save()
                            
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
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
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
            'message': message,}       
        
        inquiry_email = Inquiry.objects.values_list('email', flat=True)
        post_email = Post.objects.values_list('email', flat=True) 
                         
        if (email in post_email) and (email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
            * Both exist in Inquiry & Post *\n   
            [Quick Price]       
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
            
        elif (email in post_email) and not(email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
            * Post only exist *\n       
            [Quick Price]       
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
            
        elif not(email in post_email) and (email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
            * Inquiry only exist *\n       
            [Quick Price]       
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
        
        else:
            content = '''
            Hello, {} \n  
            * Neither in Inquiry & Post *\n       
            [Quick Price]       
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
        
        p = Inquiry(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_flight_date=return_flight_date,
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, message=message)
        p.save()        
                
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
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
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
            'message': message,           
        }
        
        inquiry_email = Inquiry.objects.values_list('email', flat=True) 
        post_email = Post.objects.values_list('email', flat=True)
                         
        if (email in inquiry_email) and (email in post_email):   
            content = '''
            Hello, {} \n
            * Both exist in Inquiry & Post *\n
            [Filled out booking form]       
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
            
        elif (email in inquiry_email) and not(email in post_email):   
            content = '''
            Hello, {} \n
            * Inquiry only exist *\n
            [Filled out booking form]       
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
            
        elif not(email in inquiry_email) and (email in post_email):   
            content = '''
            Hello, {} \n
            * Post only exist *\n
            [Filled out booking form]       
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
            
        else:
            content = '''
            Hello, {} \n
            * Neither in Inquiry & Post *\n
            [Filled out booking form]       
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
        
        p = Inquiry(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_flight_date=return_flight_date,
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, message=message)
        p.save()           

        return render(request, 'basecamp/booking_form_detail.html',
                        {'name' : name, 'email': email, })
    
    else:
        return render(request, 'basecamp/booking_form.html', {})


# Single point, Multiple points and contact  
def inquiry3(request):
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')        
        message = request.POST.get('message')     
        
        html_content = render_to_string("basecamp/html_email-inquiry3.html", 
        {'name': name, 'contact': contact,
        'email': email, 'message': message, })
        
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "inquiry from contact_us",
            text_content,
            '',
            [email, 'info@easygoshuttle.com.au']
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send()

        return render(request, 'basecamp/inquiry3.html',
                      {'name': name},
                      )

    else:
        return render(request, 'basecamp/inquiry3.html', {})


def p2p_single(request):
    if request.method == "POST":
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        date = request.POST.get('date')
        pickuptime = request.POST.get('pickuptime')
        startpoint = request.POST.get('startpoint')
        endpoint = request.POST.get('endpoint')
        passenger = request.POST.get('passenger')
        baggage = request.POST.get('baggage')
        message = request.POST.get('message')     
        
        html_content = render_to_string("basecamp/html_email-inquiry2.html", 
        {'name': name, 'contact': contact,
        'email': email, 'date': date, 'pickuptime': pickuptime,
        'startpoint': startpoint, 'endpoint': endpoint, 'passenger': passenger,
        'baggage': baggage, 'message': message, })
        
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Point to Point inquiry",
            text_content,
            '',
            [email, 'info@easygoshuttle.com.au']
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send()

        return render(request, 'basecamp/p2p_single.html',
                      {'name': name},
                      )

    else:
        return render(request, 'basecamp/p2p_single.html', {})


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
            [p2p_email, 'info@easygoshuttle.com.au']
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send()

        return render(request, 'basecamp/p2p.html',
                      {'p2p_name': p2p_name},
                      )

    else:
        return render(request, 'basecamp/p2p.html', {})


def price_detail(request):
    if request.method == "POST":
        flight_date = request.POST.get('flight_date')
        direction = request.POST.get('direction')
        suburb = request.POST.get('suburb')
        no_of_passenger = request.POST.get('no_of_passenger')
        
        
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

        message = '''
                =====================
                Someone checked price
                =====================
                Flight date: {}
                Direction: {}        
                Suburb: {}
                No of passenger: {}              
                '''.format(data['flight_date'], data['direction'],
                           data['suburb'], data['no_of_passenger'])
                
        send_mail(data['flight_date'], message, '', ['sungkam718@gmail.com'])

        return render(request, 'basecamp/inquiry1.html',
                      {'flight_date': flight_date, 'direction': direction, 'suburb': suburb,
                       'no_of_passenger': no_of_passenger},
                      )

    else:
        return render(request, 'basecamp/inquiry1.html', {})


# Post 
def confirmation_detail(request):
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
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')
        message = request.POST.get('message') 
        notice = request.POST.get('notice')       
        price = request.POST.get('price')
        paid = request.POST.get('paid')
                
        
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
            }       
        
        post_email = Post.objects.values_list('email', flat=True)
        inquiry_email = Inquiry.objects.values_list('email', flat=True) 
                         
        if (email in post_email) and (email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
            * Both exist in Inquiry & Post *\n       
            [Confirmation]       
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
            * Post only exist *\n     
            [Confirmation]       
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
            * Inquiry only exist *\n     
            [Confirmation]       
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
            * Neither in Inquiry & Post *\n    
            [Confirmation]       
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

        p = Post(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, return_flight_date=return_flight_date, 
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, notice=notice, price=price, paid=paid)
        
        p.save()

        rendering = render(request, 'basecamp/confirmation_detail.html',
                        {'name' : name, 'email': email, })  
        
        html_content = render_to_string("basecamp/html_email-confirmation.html",
                                    {'name': name, 'contact': contact, 'email': email,
                                     'flight_date': flight_date, 'flight_number': flight_number,
                                     'flight_time': flight_time, 'pickup_time': pickup_time,
                                     'return_flight_date': return_flight_date, 'return_flight_number': return_flight_number,
                                     'return_flight_time': return_flight_time, 'direction': direction, 'street': street, 
                                     'suburb': suburb, 'no_of_passenger': no_of_passenger, 'no_of_baggage': no_of_baggage,
                                     'message': message, 'notice': notice , 'price': price, 'paid': paid })
        
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(
            "Booking confirmation - EasyGo",
            text_content,
            '',
            [email, 'info@easygoshuttle.com.au']
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
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')        
        price = request.POST.get('price')
        is_confirmed_str = request.POST.get('is_confirmed')
        is_confirmed = True if is_confirmed_str == 'True' else False
        
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
            }       
        
        post_email = Post.objects.values_list('email', flat=True)
        inquiry_email = Inquiry.objects.values_list('email', flat=True) 
                         
        if (email in post_email) and (email in inquiry_email):            
                        
            content = '''
            Hello, {} \n  
            * Both exist in Inquiry & Post *\n       
            [Booking by client] >> Sending email only!      
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
            * Post only exist *\n     
            [Booking by client] >> Sending email only!       
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
            * Inquiry only exist *\n     
            [Booking by client] >> Sending email only!       
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
            * Neither in Inquiry & Post *\n    
            [Booking by client] >> Sending email only!       
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
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_flight_date=return_flight_date, 
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, message=message, 
                 price=price, is_confirmed=is_confirmed)
        
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
        user = Inquiry.objects.filter(email=email).first() 
                            
        if not user:
            return render(request, 'basecamp/500.html')   
             
        else:
            name = user.name            
            contact = user.contact            
            flight_date = user.flight_date
            flight_number = user.flight_number
            flight_time = user.flight_time
            pickup_time = user.pickup_time
            direction = user.direction
            suburb = user.suburb
            street = user.street
            no_of_passenger = user.no_of_passenger
            no_of_baggage = user.no_of_baggage
            return_flight_date = user.return_flight_date
            return_flight_number = user.return_flight_number
            return_flight_time = user.return_flight_time            
            message = user.message
            notice = user.notice
            price = user.price
            paid = user.paid            
            
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
            }       
            
            content = '''
            {} 
            clicked the 'confirm booking' \n
            >> Sending email only! \n
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
            
        p = Post(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_flight_date=return_flight_date, 
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, message=message, 
                 notice=notice, price=price, paid=paid, is_confirmed=is_confirmed, )
        
        p.save()        
               
        # send_email_delayed.apply_async(args=[name, contact, email, flight_date, flight_number, flight_time,
        #                                       pickup_time, direction, suburb, street, no_of_passenger, no_of_baggage,
        #                                       message, price, is_confirmed], countdown=30)
                
        return render(request, 'basecamp/confirm_booking_detail.html',
                        {'name' : name, 'email': email, })
        
    else:
        return render(request, 'beasecamp/confirm_booking.html', {})  
    

# From Inquiry To Post 
def retrieve_inquiry_detail(request):     
    if request.method == "POST":  
        email = request.POST.get('email')
        message = request.POST.get('message')
        price = request.POST.get('price')        
        user = Inquiry.objects.filter(email=email).first()    
        
        if not user:
            return render(request, 'basecamp/500.html')    
            
        else:
            name = user.name
            contact = user.contact            
            flight_date = user.flight_date
            flight_number = user.flight_number
            flight_time = user.flight_time
            pickup_time = user.pickup_time
            direction = user.direction
            suburb = user.suburb
            street = user.street
            no_of_passenger = user.no_of_passenger
            no_of_baggage = user.no_of_baggage
            return_flight_date = user.return_flight_date
            return_flight_number = user.return_flight_number
            return_flight_time = user.return_flight_time
            notice = user.notice
            paid = user.paid       
            
        p = Post(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_flight_date=return_flight_date, 
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, message=message, 
                 notice=notice, price=price, paid=paid)
        p.save()

        rendering = render(request, 'basecamp/retrieve_inquiry_detail.html',
                        {'name' : name, 'email': email, })        

        html_content = render_to_string("basecamp/html_email-confirmation.html",
                                    {'name': name, 'contact': contact, 'email': email,
                                     'flight_date': flight_date, 'flight_number': flight_number,
                                     'flight_time': flight_time, 'pickup_time': pickup_time,
                                     'direction': direction, 'street': street, 'suburb': suburb,
                                     'no_of_passenger': no_of_passenger, 'no_of_baggage': no_of_baggage,
                                     'message': message, 'notice': notice, 'price': price, 'paid': paid })
    
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Booking confirmation - EasyGo",
            text_content,
            '',
            [email, 'info@easygoshuttle.com.au']
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return rendering
    
    else:
        return render(request, 'beasecamp/retrieve_inquiry_error.html', {})

# From Post to Post
def retrieve_post_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')        
        no_of_passenger = request.POST.get('no_of_passenger')
        no_of_baggage = request.POST.get('no_of_baggage')
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')        
        message = request.POST.get('message')
        notice = request.POST.get('notice')        
        price = request.POST.get('price')
        paid = request.POST.get('paid')  

        user = Post.objects.filter(email=email).first() 
           
        if not user:
            return render(request, 'basecamp/500.html') 
               
        else:
            name = user.name
            contact = user.contact
            suburb = user.suburb
            street = user.street  
            
        p = Post(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_flight_date=return_flight_date, 
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, message=message, 
                 notice=notice, price=price, paid=paid)
        
        p.save()

        rendering = render(request, 'basecamp/retrieve_post_detail.html',
                        {'name' : name, 'email': email, })        

        html_content = render_to_string("basecamp/html_email-confirmation.html",
                                    {'name': name, 'contact': contact, 'email': email,
                                     'flight_date': flight_date, 'flight_number': flight_number,
                                     'flight_time': flight_time, 'pickup_time': pickup_time,
                                     'direction': direction, 'street': street, 'suburb': suburb,
                                     'no_of_passenger': no_of_passenger, 'no_of_baggage': no_of_baggage,
                                     'return_flight_date': return_flight_date, 'return_flight_number': return_flight_number,
                                     'return_flight_time': return_flight_time, 
                                     'message': message, 'notice': notice, 'price': price, 'paid': paid })
    
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Booking confirmation - EasyGo",
            text_content,
            '',
            [email, 'info@easygoshuttle.com.au']
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return rendering
    
    else:
        return render(request, 'beasecamp/retrieve_post.html', {})        


# From Post to Post
def re_confirm_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')             
        user = Post.objects.filter(email=email).first()    
        
        if not user:
            return render(request, 'basecamp/500.html') 
               
        else:
            name = user.name
            contact = user.contact
            flight_date = user.flight_date
            flight_number = user.flight_number
            flight_time = user.flight_time
            pickup_time = user.pickup_time
            direction = user.direction
            street = user.street
            suburb = user.suburb
            no_of_passenger = user.no_of_passenger
            no_of_baggage = user.no_of_baggage
            return_flight_date = user.return_flight_date
            return_flight_number = user.return_flight_number
            return_flight_time = user.return_flight_time
            message = user.message
            notice = user.notice
            price = user.price
            paid = user.paid
            
        p = Post(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_flight_date=return_flight_date, 
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, message=message, 
                 notice=notice, price=price, paid=paid)
        
        p.save()

        rendering = render(request, 'basecamp/re_confirm_detail.html',
                        {'name' : name, 'email': email, })        

        html_content = render_to_string("basecamp/html_email-confirmation.html",
                                    {'name': user.name, 'contact': user.contact, 'email': user.email,
                                     'flight_date': user.flight_date, 'flight_number': user.flight_number,
                                     'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                     'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                     'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                     'return_flight_date': user.return_flight_date, 'return_flight_number': user.return_flight_number,
                                     'return_flight_time': user.return_flight_time, 
                                     'message': user.message, 'notice': user.notice, 'price': user.price, 'paid': user.paid })
    
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Booking confirmation - EasyGo",
            text_content,
            '',
            [email, 'info@easygoshuttle.com.au']
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return rendering
    
    else:
        return render(request, 'beasecamp/re_confirm.html', {})    
     
     
# sending email only   
def re_confirm_email_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')             
        user = Post.objects.filter(email=email).first()  
         
        if not user:
            return render(request, 'basecamp/500.html')    
           
        else:
            name = user.name
        
        html_content = render_to_string("basecamp/html_email-confirmation.html",
                                    {'name': user.name, 'contact': user.contact, 'email': user.email,
                                     'flight_date': user.flight_date, 'flight_number': user.flight_number,
                                     'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                                     'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                                     'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                                     'return_flight_date': user.return_flight_date, 'return_flight_number': user.return_flight_number,
                                     'return_flight_time': user.return_flight_time, 'message': user.message, 'notice': user.notice, 
                                     'price': user.price, 'paid': user.paid })
    
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            "Booking confirmation - EasyGo",
            text_content,
            '',
            [email, 'info@easygoshuttle.com.au']
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return render(request, 'basecamp/re_confirm_email_detail.html',
                        {'name' : name, 'email': email, }) 
    
    else:
        return render(request, 'beasecamp/re_confirm_email.html', {})   


def save_data_only_detail(request):     
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
        return_flight_date = request.POST.get('return_flight_date')
        return_flight_number = request.POST.get('return_flight_number')
        return_flight_time = request.POST.get('return_flight_time')      
        message = request.POST.get('message')        
        price = request.POST.get('price')
        paid = request.POST.get('paid')
 
        p = Post(name=name, contact=contact, email=email, flight_date=flight_date, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, return_flight_date=return_flight_date, 
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, message=message, 
                 price=price, paid=paid)
        
        p.save()                   
        
        return render(request, 'basecamp/save_data_only_detail.html',{'name' : name, })
    
    else:
        return render(request, 'beasecamp/save_data_only.html', {})  
    
    
# From Inquiry to Inquiry 
def retrieve_inquiry_To_inquiry_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        flight_date = request.POST.get('flight_date')
        flight_number = request.POST.get('flight_number')
        flight_time = request.POST.get('flight_time')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction')        
        no_of_passenger = request.POST.get('no_of_passenger')        
        message = request.POST.get('message')        
        price = request.POST.get('price')  

        user = Inquiry.objects.filter(email=email).first()    
        
        if not user:
            return render(request, 'basecamp/500.html')       
        
        else:
            name = user.name
            contact = user.contact
            suburb = user.suburb
            street = user.street
            no_of_baggage = user.no_of_baggage
            notice = user.notice
            
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
        return render(request, 'beasecamp/retrieve_inquiry_to_inquiry.html', {})         


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
            return render(request, 'basecamp/500.html')  
             
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
        is_confirmed_str = request.POST.get('is_confirmed')
        is_confirmed = True if is_confirmed_str == 'True' else False
        
        user = Post.objects.filter(email=email).first()    
        
        if not user:
            return render(request, 'basecamp/501.html')    
            
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
                 no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, notice=notice, price=price, paid=paid, is_confirmed=is_confirmed)
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
        
        user = Post.objects.filter(email=email).first()    
        
        if not user:
            return render(request, 'basecamp/500.html')    
            
        else: 
            
            html_content = render_to_string("basecamp/html_email-invoice.html",
                                        {'notice': user.notice, 'name': user.name, 'contact': user.contact, 
                                         'email': user.email, 'direction': user.direction, 'flight_date': user.flight_date, 
                                         'flight_time': user.flight_time, 'pickup_time': user.pickup_time, 'street': user.street, 
                                         'suburb': user.suburb, 'no_of_passenger': user.no_of_passenger, 'price': user.price, 'paid': user.paid })

            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                "Tax Invoice - EasyGo",
                text_content,
                '',
                [email, 'info@easygoshuttle.com.au']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            return render(request, 'basecamp/return_trip.html',
                            {'email': email, })  
    
    else:
        return render(request, 'beasecamp/invoice.html', {})  


