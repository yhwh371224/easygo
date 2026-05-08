from datetime import date
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
from utils.email import send_text_email
from utils.telegram import send_telegram_sync
from django.db.models import Q
from django.http import JsonResponse
from main.settings import RECIPIENT_EMAIL
from basecamp.area import get_suburbs
from regions.models import Region, Terminal
from basecamp.basecamp_utils import (
    is_ajax, parse_date,
    verify_turnstile, get_sorted_suburbs,
    render_inquiry_done, booking_success_response, require_turnstile,
)
from articles.models import Post
from django_ratelimit.decorators import ratelimit
from basecamp.views.inquirys import _get_request_region, _resolve_terminal


def _airport_terminals_for_request(request):
    region = getattr(request, 'region', None)
    if not region:
        return Terminal.objects.none()
    return Terminal.objects.filter(
        airport__regions=region
    ).select_related('airport').order_by('type', 'name')


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def price_detail(request):
    latest_post = Post.objects.filter(status='published').order_by('-created_at').first()
    if request.method == "POST":
        post_region = _get_request_region(request)
        if not post_region:
            region_slug = request.POST.get('region')
            if region_slug:
                post_region = Region.objects.filter(slug=region_slug, is_active=True).first()

        # Sydney fallback
        if not post_region:
            post_region = Region.objects.filter(slug='sydney', is_active=True).first()

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
            if getattr(request, 'region', None):
                return redirect('regions:home', region_slug=request.region.slug)
            return render(request, 'basecamp/home.html', {
                'error_message': str(e),
                'suburbs': get_suburbs(),
                'home_suburbs': get_sorted_suburbs(),
                'airport_terminals': _airport_terminals_for_request(request),
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

        region = request.region

        if not region:
            start_terminal = None
            end_terminal = None
        else:
            start_terminal = _resolve_terminal(region, start_point)
            end_terminal = _resolve_terminal(region, end_point)

        if start_terminal:
            normalized_start_point = 'Airport'

        if end_terminal:
            normalized_end_point = 'Airport'

        condition_met = not (
            (normalized_start_point in ['Overseas cruise terminal', 'WhiteBay cruise terminal'] and normalized_end_point == 'Airport') or
            (normalized_start_point == 'Airport' and normalized_end_point in ['Overseas cruise terminal', 'WhiteBay cruise terminal'])
        )

        context = {
            'pickup_date': pickup_date.strftime('%Y-%m-%d'),
            'start_point': normalized_start_point,
            'end_point': normalized_end_point,
            # Keep original values (e.g., terminal IDs) for downstream direction resolution.
            'original_start_point': start_point,
            'original_end_point': end_point,
            'no_of_passenger': no_of_passenger,
            'condition_met': condition_met,
            'latest_post': latest_post,
        }

        if region is not None:
            context['region'] = region
            return render(request, 'regions/inquiry/inquiry1.html', context)

        return render(request, 'basecamp/booking/inquiry1.html', context)

    else:
        if getattr(request, 'region', None):
            return redirect('regions:home', region_slug=request.region.slug)
        # Region-less legacy home can still render, but it won't allow terminal-based pricing.
        return render(request, 'basecamp/home.html', {
            'suburbs': get_suburbs(),
            'home_suburbs': get_sorted_suburbs(),
            'airport_terminals': _airport_terminals_for_request(request),
            'google_review_url': settings.GOOGLE_REVIEW_URL,
            'latest_post': latest_post,
        })
    

# Contact form
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_turnstile
def contact_submit(request):
    if request.method == "POST":
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

        telegram_text = (
            f"📬 *New Contact Form*\n"
            f"Name: {data['name']}\n"
            f"Email: {data['email']}\n"
            f"Message: {data['message']}"
        )
        send_telegram_sync(telegram_text)

        return booking_success_response(request)
    else:
        return render(request, 'basecamp/pages/contact_form.html', {})
    

    