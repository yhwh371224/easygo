from datetime import date
from django.shortcuts import render
from django.conf import settings
from utils.email import send_text_email
from django.db.models import Q
from django.http import JsonResponse
from main.settings import RECIPIENT_EMAIL
from basecamp.area import get_suburbs
from basecamp.area_home import get_home_suburbs
from basecamp.basecamp_utils import (
    is_ajax, parse_date,
    verify_turnstile, get_sorted_suburbs,
    render_inquiry_done, booking_success_response, require_turnstile,
)
from articles.models import Post
from django_ratelimit.decorators import ratelimit


@ratelimit(key='ip', rate='5/m', method='POST', block=False)
def price_detail(request):
    sorted_suburbs = get_sorted_suburbs()
    latest_post = Post.objects.filter(status='published').order_by('-created_at').first()
    if request.method == "POST":
        if getattr(request, 'limited', False):
            if is_ajax(request):
                return JsonResponse({'success': False, 'message': 'Too many requests. Please wait a moment and try again.'}, status=429)
            return render(request, 'basecamp/403.html', status=429)
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
                'google_review_url': settings.GOOGLE_REVIEW_URL, 
                'latest_post': latest_post, 
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
            'condition_met': condition_met,
            'latest_post': latest_post,
        }

        return render(request, 'basecamp/booking/inquiry1.html', context)

    else:
        return render(request, 'basecamp/home.html', {
            'home_suburbs': sorted_suburbs,
            'google_review_url': settings.GOOGLE_REVIEW_URL, 
            'latest_post': latest_post,
            'suburbs': get_suburbs(), 
        })
    

# Contact form
@ratelimit(key='ip', rate='5/m', method='POST', block=False)
@require_turnstile
def contact_submit(request):
    if request.method == "POST":
        if getattr(request, 'limited', False):
            if is_ajax(request):
                return JsonResponse({'success': False, 'message': 'Too many requests. Please wait a moment and try again.'}, status=429)
            return render(request, 'basecamp/403.html', status=429)

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

        send_text_email(subject, message, [RECIPIENT_EMAIL])
        
        return booking_success_response(request)
    else:
        return render(request, 'basecamp/pages/contact_form.html', {})