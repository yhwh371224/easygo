import requests

from datetime import timedelta
from functools import wraps

from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from main import settings
from blog.models import Inquiry, Post


def verify_turnstile(turnstile_response, remoteip=None):
    if getattr(settings, 'TURNSTILE_DISABLED', False):
        return True

    data = {
        'secret': settings.CLOUDFLARE_TURNSTILE_SECRET_KEY,
        'response': turnstile_response,
    }
    if remoteip:
        data['remoteip'] = remoteip

    r = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=data)
    return r.json().get('success', False)


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def render_inquiry_done(request):
    return render(request, 'basecamp/inquiry_done.html', {
        'google_review_url': settings.GOOGLE_REVIEW_URL,
    })


def booking_success_response(request):
    if is_ajax(request):
        return JsonResponse({'success': True, 'message': 'Inquiry submitted successfully.'})
    return render_inquiry_done(request)


def require_turnstile(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.method == 'POST':
            token = request.POST.get('cf-turnstile-response', '')
            ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
            if not verify_turnstile(token, ip):
                return JsonResponse({'success': False, 'error': 'Security verification failed. Please try again.'})
        return view_func(request, *args, **kwargs)
    return _wrapped


def is_duplicate_submission(model_class, email, seconds=2):
    return model_class.objects.filter(
        email=email,
        created__gte=timezone.now() - timedelta(seconds=seconds)
    ).exists()


def get_customer_status(email, name, subject_prefix=""):
    inquiry_exists = Inquiry.objects.filter(email=email).exists()
    post_exists = Post.objects.filter(email=email).exists()
    is_existing = inquiry_exists or post_exists
    status_message = "Exist in Inquiry or Post *" if is_existing else "Neither in Inquiry & Post *"
    kind = "Existing" if is_existing else "New"
    subject = f"{subject_prefix}{kind} Customer - {name}" if subject_prefix else f"{kind} - {name}"
    return status_message, subject


def parse_one_based_index(raw_index):
    try:
        return int(raw_index) - 1
    except (TypeError, ValueError):
        raise ValueError("Invalid index value")


def resolve_payment_flags(prepay_raw, cash_raw, *users):
    form_prepay = (prepay_raw == 'True') if prepay_raw is not None else False
    form_cash = (cash_raw == 'True') if cash_raw is not None else False
    final_prepay = form_prepay or any(bool(u.prepay) for u in users)
    final_cash = form_cash or any(bool(u.cash) for u in users)
    return final_prepay, final_cash
