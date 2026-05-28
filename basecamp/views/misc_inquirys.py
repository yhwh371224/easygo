import logging
from datetime import date
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
from utils.email import send_text_email

logger = logging.getLogger(__name__)
from utils.telegram import send_telegram_sync
from django.db.models import Q
from django.http import JsonResponse
from main.settings import RECIPIENT_EMAIL
from basecamp.area import get_suburbs
from regions.models import Region, RegionSuburb, Terminal, CruiseTerminal
from basecamp.basecamp_utils import (
    is_ajax, parse_date,
    verify_turnstile, get_sorted_suburbs,
    render_inquiry_done, booking_success_response, require_turnstile,
)
from articles.models import Post
from django_ratelimit.decorators import ratelimit
from basecamp.views.inquirys import _get_request_region, _resolve_terminal, _resolve_cruise_terminal


def _airport_terminals_for_request(request):
    region = getattr(request, 'region', None)
    if not region:
        return Terminal.objects.none()
    return Terminal.objects.filter(
        airport__regions=region
    ).select_related('airport').order_by('type', 'name')


def _cruise_terminals_for_request(request):
    region = getattr(request, 'region', None)
    if region:
        return CruiseTerminal.objects.filter(region=region)
    # Basecamp home is Sydney-specific; fall back to Sydney cruise terminals.
    return CruiseTerminal.objects.filter(region__slug='sydney')


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

        request.region = post_region

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
            if post_region and post_region.slug != 'sydney':
                return redirect('regions:home', region_slug=request.region.slug)
            return render(request, 'basecamp/home.html', {
                'error_message': str(e),
                'suburbs': get_suburbs(),
                'carousel_suburbs': get_suburbs(),
                'home_suburbs': RegionSuburb.objects.filter(region__slug='sydney', is_active=True).order_by('-is_pinned', 'sort_order', 'name'),
                'airport_terminals': _airport_terminals_for_request(request),
                'cruise_terminals': _cruise_terminals_for_request(request),
                'latest_post': latest_post,
                'start_point_value': start_point if start_point != 'Select your option' else '',
                'end_point_value': end_point if end_point != 'Select your option' else '',
                'no_of_passenger_value': no_of_passenger,
            })

        request.session['original_start_point'] = start_point
        request.session['original_end_point'] = end_point

        region = request.region

        if region:
            start_terminal = _resolve_terminal(region, start_point)
            end_terminal = _resolve_terminal(region, end_point)
            start_cruise = _resolve_cruise_terminal(region, start_point)
            end_cruise = _resolve_cruise_terminal(region, end_point)
        else:
            start_terminal = end_terminal = start_cruise = end_cruise = None

        is_start_airport = bool(start_terminal)
        is_end_airport = bool(end_terminal)
        is_start_cruise = bool(start_cruise)
        is_end_cruise = bool(end_cruise)

        condition_met = not (
            (is_start_cruise and is_end_airport) or
            (is_start_airport and is_end_cruise)
        )

        start_display = (start_terminal.name if start_terminal else
                         start_cruise.name if start_cruise else start_point)
        end_display = (end_terminal.name if end_terminal else
                       end_cruise.name if end_cruise else end_point)

        context = {
            'pickup_date': pickup_date.strftime('%Y-%m-%d'),
            'start_point': start_point,
            'end_point': end_point,
            'start_point_display': start_display,
            'end_point_display': end_display,
            'original_start_point': start_point,
            'original_end_point': end_point,
            'no_of_passenger': no_of_passenger,
            'condition_met': condition_met,
            'is_start_airport': is_start_airport,
            'is_end_airport': is_end_airport,
            'is_start_cruise': is_start_cruise,
            'is_end_cruise': is_end_cruise,
            'latest_post': latest_post,
        }

        if region is not None:
            context['region'] = region
            context['cruise_terminals'] = CruiseTerminal.objects.filter(region=region)
            return render(request, 'regions/inquiry/inquiry1.html', context)

        return render(request, 'basecamp/booking/inquiry1.html', context)

    else:
        if getattr(request, 'region', None):
            return redirect('regions:home', region_slug=request.region.slug)
        # Region-less legacy home can still render, but it won't allow terminal-based pricing.
        return render(request, 'basecamp/home.html', {
            'suburbs': get_suburbs(),
            'carousel_suburbs': get_suburbs(),
            'home_suburbs': RegionSuburb.objects.filter(region__slug='sydney', is_active=True).order_by('-is_pinned', 'sort_order', 'name'),
            'airport_terminals': _airport_terminals_for_request(request),
            'cruise_terminals': _cruise_terminals_for_request(request),
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

        try:
            send_text_email(subject, message, [RECIPIENT_EMAIL])
        except Exception:
            logger.exception("contact_submit: failed to send email for %s", data['email'])

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
    

    