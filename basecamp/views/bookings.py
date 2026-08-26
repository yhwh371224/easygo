import asyncio
import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from decimal import Decimal
from basecamp.views.inquirys import _get_request_region
from django_ratelimit.decorators import ratelimit
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from blog.models import Post, Inquiry, Driver
from blog import dunning
from blog.blog_utils import resolve_booking_driver
from blog.tasks import send_post_confirmation_email_task
from regions.models import Region
from basecamp.basecamp_utils import (
    is_ajax, parse_baggage, parse_date,
    to_bool, verify_turnstile,
    render_inquiry_done, booking_success_response, require_turnstile,
    is_duplicate_submission, parse_booking_dates, get_client_ip,
)
from utils import email
from utils.telegram import send_telegram_notification, get_ip_info

logger = logging.getLogger(__name__)

from regions.models import RequestLog

# Quick rebook — 차량이 13인승까지라 그 이상은 폼으로 받지 않고 메일로 안내한다.
MAX_REBOOK_PASSENGERS = 13
SUPPORT_EMAIL = 'info@easygoshuttle.com.au'


def _posted_stop_addresses(request):
    """폼에 입력된 경유지 주소들. step2 를 에러로 다시 그릴 때 입력을 살리는 용도."""
    try:
        count = int(request.POST.get('extra_stop') or 0)
    except ValueError:
        count = 0
    return [
        request.POST.get(f'extra_stop_address_{i}', '').strip()
        for i in range(1, max(count, 0) + 1)
    ]


def _normalize_pax(value):
    """인원수 문자열 → 1~MAX_REBOOK_PASSENGERS 범위의 int.

    범위 밖이거나 숫자가 아니면 None. 예전 예약의 no_of_passenger 는 CharField 라
    '8 people' 같은 값도 들어있어 셀렉트 기본값으로 그대로 쓸 수 없다.
    """
    try:
        pax = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if 1 <= pax <= MAX_REBOOK_PASSENGERS:
        return pax
    return None


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_POST
def confirm_booking_detail(request):
    logger.info(
        f"[BOOKING] IP={get_client_ip(request)} "
        f"path={request.path} "
        f"email={request.POST.get('email')}"
    )
    
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

    users = Inquiry.objects.filter(booker_email__iexact=email)
    if not users.exists():
        users = Inquiry.objects.filter(email__iexact=email)

    if users.exists() and 0 <= index < len(users):
        user = users[index]
    else:
        return render(request, 'basecamp/email/email_error_confirmbooking.html')

    # 기존 데이터
    name = user.name
    booker_name = user.booker_name
    booer_email = user.booker_email
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
    surcharge = user.surcharge
    paid = user.paid
    private_ride = user.private_ride
    region = user.region
    special_items = user.special_items or {}
    customer_history = getattr(user, 'customer_history', "")
    extra_stop = user.extra_stop or 0
    extra_stop_addresses = user.extra_stop_addresses or []
    same_extra_stop = user.same_extra_stop

    # ── Inquiry 단계에서 이미 선결제로 확정된 건 → 그대로 승계 ──
    # 관리자가 가격 넣고 저장하면 prepay=True 가 찍히고 prepay 안내메일이 나가는데,
    # 손님이 그 링크 대신 일반 confirm_booking 으로 들어와도 조건은 유지되어야 한다.
    if user.prepay:
        cash = False
        prepay = True
    # ─────────────────────────────────

    # ── 도착편 + 첫이용 → prepay 강제 ──
    is_arrival = (direction or "").startswith("Pickup from")
    has_completed_trip = Post.objects.filter(
        email__iexact=email,
        cancelled=False,
        pending=False,
    ).exists()
    is_first_time = not has_completed_trip

    if is_arrival and is_first_time:
        cash = False
        prepay = True
    # ─────────────────────────────────

    try:
        pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date, return_pickup_date)
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)})

    # ── 초임박 예약(픽업 24h 이내) → 선결제 강제 ──
    # 사다리(Payment→Urgent→Final→취소)를 돌릴 시간이 없어 결제 기회도 없이
    # 취소되는 것을 막기 위해, 이런 건은 결제해야 확정되도록 한다(방향 무관).
    pickup_dt = dunning.combine_pickup(pickup_date_obj, pickup_time)
    if dunning.is_prepay_required_at_booking(pickup_dt):
        cash = False
        prepay = True
    # ─────────────────────────────────

    # 최종 가격 계산
    if price in [None, ""]:
        final_price = "TBA"
        toll_value = ""
        surcharge_value = ""
    else:
        try:
            final_price = float(price)
            if toll:
                final_price += float(toll)
            if surcharge:
                final_price += float(surcharge)
        except Exception:
            final_price = price
        toll_value = "toll included" if toll else ""
        surcharge_value = "surcharge included" if surcharge else ""

    # pending 상태 결정
    if paid or cash or prepay:
        pending = False
    else:
        pending = True  

    driver = resolve_booking_driver(direction, suburb, region)

    is_confirmed = False

    # Post 모델 저장
    p = Post(
        name=name, contact=contact, email=email, company_name=company_name, email1=email1,
        booker_name=booker_name, booker_email=booer_email, booker_contact=getattr(user, 'booker_contact', None),
        pickup_date=pickup_date_obj, flight_number=flight_number, flight_time=flight_time, pickup_time=pickup_time,
        direction=direction, suburb=suburb, street=street, start_point=start_point, end_point=end_point,
        cruise=cruise, no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage,
        return_direction=return_direction, private_ride=private_ride,
        return_pickup_date=return_pickup_date_obj, return_flight_number=return_flight_number,
        return_flight_time=return_flight_time, return_pickup_time=return_pickup_time,
        return_start_point=return_start_point, return_end_point=return_end_point,
        message=message, notice=notice, price=final_price, toll=toll_value,
        surcharge=surcharge_value, prepay=prepay, pending=pending,
        paid=paid, cash=cash, is_confirmed=is_confirmed, driver=driver, region=region,
        special_items=special_items, extra_stop=extra_stop, extra_stop_addresses=extra_stop_addresses,
        same_extra_stop=same_extra_stop, customer_history=customer_history,
    )

    p.save()

    user.delete()

    ip = get_client_ip(request)
    ip_info = get_ip_info(ip)
    try:
        asyncio.run(send_telegram_notification(
            f"Clicked the confirm button:\n"
            f"IP: `{ip}`\n"
            f"Location: {ip_info}"
        ))
    except Exception as e:
        logger.error(f"[TELEGRAM] Failed to send: {e}")

    return render_inquiry_done(request)


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_POST
def confirm_booking_prepay_detail(request):
    logger.info(
        f"[BOOKING PREPAY] IP={get_client_ip(request)} "
        f"path={request.path} "
        f"email={request.POST.get('email')}"
    )

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

    users = Inquiry.objects.filter(booker_email__iexact=email)
    if not users.exists():
        users = Inquiry.objects.filter(email__iexact=email)

    if users.exists() and 0 <= index < len(users):
        user = users[index]
    else:
        return render(request, 'basecamp/email/email_error_confirmbooking.html')

    name = user.name
    booker_name = user.booker_name
    booer_email = user.booker_email
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
    surcharge = user.surcharge
    paid = user.paid
    private_ride = user.private_ride
    region = user.region
    special_items = user.special_items or {}
    customer_history = getattr(user, 'customer_history', "")
    extra_stop = user.extra_stop or 0
    extra_stop_addresses = user.extra_stop_addresses or []
    same_extra_stop = user.same_extra_stop

    # prepay 경로이므로 항상 prepay 강제
    cash = False
    prepay = True

    try:
        pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date, return_pickup_date)
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)})

    if price in [None, ""]:
        final_price = "TBA"
        toll_value = ""
        surcharge_value = ""
    else:
        try:
            final_price = float(price)
            if toll:
                final_price += float(toll)
            if surcharge:
                final_price += float(surcharge)
        except Exception:
            final_price = price
        toll_value = "toll included" if toll else ""
        surcharge_value = "surcharge included" if surcharge else ""

    if paid or cash or prepay:
        pending = False
    else:
        pending = True

    driver = resolve_booking_driver(direction, suburb, region)

    is_confirmed = False

    p = Post(
        name=name, contact=contact, email=email, company_name=company_name, email1=email1,
        booker_name=booker_name, booker_email=booer_email, booker_contact=getattr(user, 'booker_contact', None),
        pickup_date=pickup_date_obj, flight_number=flight_number, flight_time=flight_time, pickup_time=pickup_time,
        direction=direction, suburb=suburb, street=street, start_point=start_point, end_point=end_point,
        cruise=cruise, no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage,
        return_direction=return_direction, private_ride=private_ride,
        return_pickup_date=return_pickup_date_obj, return_flight_number=return_flight_number,
        return_flight_time=return_flight_time, return_pickup_time=return_pickup_time,
        return_start_point=return_start_point, return_end_point=return_end_point,
        message=message, notice=notice, price=final_price, toll=toll_value,
        surcharge=surcharge_value, prepay=prepay, pending=pending,
        paid=paid, cash=cash, is_confirmed=is_confirmed, driver=driver, region=region,
        special_items=special_items, extra_stop=extra_stop, extra_stop_addresses=extra_stop_addresses,
        same_extra_stop=same_extra_stop, customer_history=customer_history,
    )

    p.save()

    user.delete()

    # 결제 여부와 무관하게, confirm 클릭 10분 후 confirmation email 발송.
    # 이미 다른 경로(예: admin is_confirmed)로 발송됐다면 태스크 내 sent_email
    # 플래그가 막아주므로 중복 걱정 없음.
    send_post_confirmation_email_task.apply_async(args=[p.pk], countdown=600)

    ip = get_client_ip(request)
    ip_info = get_ip_info(ip)
    try:
        asyncio.run(send_telegram_notification(
            f"Clicked the confirm button (prepay):\n"
            f"IP: `{ip}`\n"
            f"Location: {ip_info}"
        ))
    except Exception as e:
        logger.error(f"[TELEGRAM] Failed to send: {e}")

    params = urlencode({'name': name, 'amount': final_price})
    return redirect(f"/payonline/?{params}")


# For Return Trip
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_POST
@require_turnstile
def return_trip_detail(request):    
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
    notice = request.POST.get('notice', '')
    price = request.POST.get('price', '')
    toll = request.POST.get('toll', '')
    surcharge = request.POST.get('surcharge', '')
    cash = to_bool(request.POST.get('cash', ''))
    prepay = to_bool(request.POST.get('prepay', ''))
    return_direction = request.POST.get('return_direction', '')
    return_flight_number = request.POST.get('return_flight_number', '')
    return_flight_time = request.POST.get('return_flight_time', '')
    return_pickup_time = request.POST.get('return_pickup_time', '')
    return_start_point = request.POST.get('return_start_point', '')
    return_end_point = request.POST.get('return_end_point', '') 

    # ✅ 중복 제출 방지
    if is_duplicate_submission(Post, email):
        return JsonResponse({'success': False, 'message': 'Duplicate inquiry recently submitted. Please wait before trying again.'})
    
    user = Post.objects.filter(Q(email__iexact=email)).first()        
    if not user:
        return render(request, '403.html')    
        
    else:
        name = user.name
        company_name = user.company_name
        contact = user.contact
        suburb = user.suburb
        street = user.street
        no_of_passenger = user.no_of_passenger
        no_of_baggage = user.no_of_baggage
        region = user.region
        extra_stop = user.extra_stop or 0
        same_extra_stop = user.same_extra_stop
        extra_stop_addresses = user.extra_stop_addresses if same_extra_stop else []
        special_items = user.special_items or {}
        if not start_point:
            start_point = user.start_point
        if not end_point:
            end_point = user.end_point
        
        # message 추가 (기존 내용 보존)
        if message and user.message:
            message = f"{user.message} | {message}"
        elif not message:
            message = user.message

        # notice 추가 (기존 내용 보존)
        if notice and user.notice:
            notice = f"{user.notice} | {notice}"
        elif not notice:
            notice = user.notice

        # 날짜 파싱 (admin form — 과거 날짜 허용)
        try:
            pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date_str, return_pickup_date_str, allow_past=True)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
    driver = resolve_booking_driver(direction, suburb, region)

    p = Post(name=name, company_name=company_name, contact=contact, email=email, pickup_date=pickup_date_obj, flight_number=flight_number, flight_time=flight_time,
                pickup_time=pickup_time, start_point=start_point, end_point=end_point, direction=direction, suburb=suburb, street=street,
                no_of_passenger=no_of_passenger, no_of_baggage=no_of_baggage, message=message, cash=cash, prepay=prepay, return_direction=return_direction,
                return_pickup_date=return_pickup_date_obj, return_flight_number=return_flight_number, return_flight_time=return_flight_time,
                return_pickup_time=return_pickup_time, return_start_point=return_start_point, return_end_point=return_end_point, driver=driver,
                price=price, toll=toll, surcharge=surcharge, region=region,
                extra_stop=extra_stop, same_extra_stop=same_extra_stop, extra_stop_addresses=extra_stop_addresses,
                special_items=special_items)

    p.save()

    return JsonResponse({'success': True, 'redirect_url': '/inquiry_done/'})



# STEP 1 — POST from home tab
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_POST
def quick_rebook_step1(request, region_slug=None):
    email           = request.POST.get('email', '').strip()
    pickup_date     = request.POST.get('pickup_date', '').strip()
    pickup_time     = request.POST.get('pickup_time', '').strip()
    no_of_passenger = request.POST.get('no_of_passenger', '').strip()

    error_redirect = request.POST.get('error_redirect', '').strip()
    _ALLOWED_ERROR_REDIRECTS = {'/rebook/'}

    def render_step1_error(msg):
        request.session['rebook_error'] = msg
        if error_redirect in _ALLOWED_ERROR_REDIRECTS:
            return redirect(error_redirect)
        region = _get_request_region(request)
        if region:
            return redirect(f'/{region.slug}/')
        return redirect('basecamp:home')

    if not email:
        return render_step1_error('Please enter your email address.')

    if not pickup_date:
        return render_step1_error('Please select a pickup date.')

    try:
        pickup_date_obj = parse_date(pickup_date, field_name='Pickup Date', required=True)
    except ValueError as e:
        return render_step1_error(str(e))

    # 인원수 — 홈/네비바/rebook 폼 공통. 1~13명만 받고, 그 이상은 메일로 안내.
    if not no_of_passenger:
        return render_step1_error('Please select the number of passengers.')

    pax = _normalize_pax(no_of_passenger)
    if pax is None:
        return render_step1_error(
            f'Please select 1-{MAX_REBOOK_PASSENGERS} passengers. '
            f'For larger groups, email us at {SUPPORT_EMAIL} and we will arrange it for you.'
        )
    no_of_passenger = str(pax)

    previous = Post.objects.filter(
        email__iexact=email,
        cancelled=False,
    ).first()

    if not previous:
        request.session['rebook_error'] = (
            'No previous booking found for this email. '
            'Please use New Booking.'
        )
        if error_redirect in _ALLOWED_ERROR_REDIRECTS:
            return redirect(error_redirect)
        region = _get_request_region(request)
        if region:
            return redirect(f'/{region.slug}/')
        return redirect('basecamp:home')

    logger.info(f"[QUICK REBOOK STEP1] email={email} found previous Post id={previous.id}")

    return render(request, 'basecamp/quick_rebook_step2.html', {
        'previous'       : previous,
        'email'          : email,
        'pickup_date'    : pickup_date,
        'pickup_date_obj': pickup_date_obj,
        # 항공편은 지난 예약 값을 미리 채워주고, step2 폼에서 반드시 고칠 수 있게 둔다.
        'flight_number'  : previous.flight_number or '',
        'pickup_time'    : pickup_time,
        'no_of_passenger': no_of_passenger,
        'passenger_choices': range(1, MAX_REBOOK_PASSENGERS + 1),
        'direction'      : previous.direction,
        # 지난 예약에 direction 이 없으면 공항을 안 거친 지점간 예약이었다는 뜻.
        'is_point_to_point': not (previous.direction or '').strip(),
        'start_point'    : previous.start_point or '',
        'end_point'      : previous.end_point or '',
        'active_regions' : Region.objects.filter(is_active=True),
        'error'          : None,
    })


# STEP 2 — POST from quick_rebook_step2.html form submission
# require_turnstile 데코레이터는 실패 시 JSON 을 돌려준다 — AJAX 인 inquiry 폼에는 맞지만
# 이 폼은 일반 POST 라 고객이 원시 JSON 을 보게 된다. 여기서는 직접 검사해서
# step2 를 에러와 함께 다시 보여준다(그래야 재예약을 포기하고 나가지 않는다).
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@require_POST
def quick_rebook_confirm(request, region_slug=None):

    # 1. Step 1 에서 넘어온 값
    email           = request.POST.get('email', '').strip()
    pickup_date_str = request.POST.get('pickup_date', '').strip()
    flight_number   = request.POST.get('flight_number', '').strip()
    pickup_time     = request.POST.get('pickup_time', '').strip()

    # 2. Step 2 폼에서 받는 값 (수정 가능)
    contact         = request.POST.get('contact', '').strip()
    no_of_passenger = request.POST.get('no_of_passenger', '').strip()
    no_of_baggage   = request.POST.get('no_of_baggage', '').strip()
    direction       = request.POST.get('direction', '').strip()
    suburb          = request.POST.get('suburb', '').strip()
    flight_time     = request.POST.get('flight_time', '').strip()
    message         = request.POST.get('message', '').strip()

    # 공항을 안 거치는 지점간(point to point) 예약도 있다. 이 경우 메인 예약 흐름과
    # 동일하게 direction/suburb 는 비우고 start_point/end_point 에 실제 지점을 담는다.
    trip_type         = request.POST.get('trip_type', '').strip()
    is_point_to_point = trip_type == 'point_to_point'
    start_point       = request.POST.get('start_point', '').strip()
    end_point         = request.POST.get('end_point', '').strip()

    # Return trip
    has_return           = request.POST.get('has_return') == 'on'
    return_date_str      = request.POST.get('return_pickup_date', '').strip()
    return_flight_number = request.POST.get('return_flight_number', '').strip()
    return_flight_time   = request.POST.get('return_flight_time', '').strip()
    return_pickup_time   = request.POST.get('return_pickup_time', '').strip()

    # 3. DB에서 직접 조회 — 안전하고 정확
    previous_id = request.POST.get('previous_id')
    previous = Post.objects.filter(id=previous_id, email__iexact=email, cancelled=False).first()
    if not previous:
        return redirect('basecamp:home')

    def render_step2_error(msg):
        """입력값을 그대로 살려 step2 를 다시 보여준다."""
        return render(request, 'basecamp/quick_rebook_step2.html', {
            'previous'          : previous,
            'email'             : email,
            'pickup_date'       : pickup_date_str,
            'flight_number'     : flight_number,
            'pickup_time'       : pickup_time,
            'direction'         : direction,
            'no_of_passenger'   : no_of_passenger,
            'passenger_choices' : range(1, MAX_REBOOK_PASSENGERS + 1),
            'start_point'       : start_point,
            'end_point'         : end_point,
            'is_point_to_point' : is_point_to_point,
            # 고객이 고쳐 넣은 값들 — 다시 그릴 때 지난 예약 값으로 되돌아가면 안 된다.
            'contact'           : contact,
            'no_of_baggage'     : no_of_baggage,
            'message'           : message,
            'extra_stop'        : request.POST.get('extra_stop', ''),
            'extra_stop_addresses': _posted_stop_addresses(request),
            'active_regions'    : Region.objects.filter(is_active=True),
            'error'             : msg,
        })

    # Turnstile 검증 — 저장 전에, 그리고 step2 를 다시 그릴 수 있는 시점에서.
    if not verify_turnstile(request.POST.get('cf-turnstile-response', ''), get_client_ip(request)):
        logger.warning(
            "[QUICK REBOOK CONFIRM] turnstile failed email=%s ip=%s", email, get_client_ip(request),
        )
        return render_step2_error(
            'Security check failed. Please complete the checkbox below and submit again.'
        )

    # 중복 제출 방지
    if is_duplicate_submission(Post, email):
        return render_step2_error('Duplicate submission. Please wait a moment and try again.')

    # 인원수 검증 — step1 과 동일 규칙(1~13명, 초과는 메일 안내)
    pax = _normalize_pax(no_of_passenger)
    if pax is None:
        return render_step2_error(
            f'Please select 1-{MAX_REBOOK_PASSENGERS} passengers. '
            f'For larger groups, email us at {SUPPORT_EMAIL} and we will arrange it for you.'
        )
    no_of_passenger = str(pax)

    # 경로 검증 — 공항편이면 direction, 지점간이면 start/end point 가 있어야 한다.
    if is_point_to_point:
        direction = ''
        suburb    = ''
        if not start_point or not end_point:
            return render_step2_error('Please enter both the pick-up and drop-off points.')
    else:
        start_point = ''
        end_point   = ''
        if not direction:
            return render_step2_error('Please select the direction of your airport trip.')

    previous_name  = previous.name
    base_price = Decimal(previous.price)
    previous_price = base_price * 2 if (has_return and return_pickup_time) else base_price
    previous_street = previous.street or ''
    region         = previous.region
    extra_stop     = int(request.POST.get('extra_stop') or previous.extra_stop or 0)
    same_extra_stop = request.POST.get('same_extra_stop') == '1'
    extra_stop_addresses = [
        a for i in range(1, extra_stop + 1)
        if (a := request.POST.get(f'extra_stop_address_{i}', '').strip())
    ]
    if not extra_stop_addresses and same_extra_stop:
        extra_stop_addresses = previous.extra_stop_addresses
    special_items  = previous.special_items or {}

    # Driver 배정
    driver = resolve_booking_driver(direction, suburb, region)

    # 날짜 파싱
    try:
        pickup_date_obj = parse_date(pickup_date_str, field_name='Pickup Date', required=True)
    except ValueError as e:
        return render_step2_error(str(e))

    return_date_obj = None
    if has_return and return_date_str:
        try:
            return_date_obj = parse_date(return_date_str, field_name='Return Date', required=False)
        except ValueError:
            return_date_obj = None

    # ── 초임박 재예약(픽업 24h 이내) → 선결제 강제 ──
    # confirm_booking_detail 과 동일 규칙. 사다리를 돌릴 시간이 없어 결제 기회도
    # 없이 취소되는 것을 막는다. 선결제 강제 시 pending 은 해제(메인 경로와 동일).
    pickup_dt = dunning.combine_pickup(pickup_date_obj, pickup_time)
    prepay = dunning.is_prepay_required_at_booking(pickup_dt)
    pending = not prepay

    # Post 저장
    p = Post(
        name            = previous_name,
        contact         = contact,
        email           = email,
        pickup_date     = pickup_date_obj,
        flight_number   = flight_number,
        flight_time     = flight_time,
        pickup_time     = pickup_time,
        direction       = direction,
        suburb          = suburb,
        start_point     = start_point,
        end_point       = end_point,
        street          = previous_street,
        no_of_passenger = no_of_passenger,
        no_of_baggage   = no_of_baggage,
        message         = message,
        region          = region,
        price           = previous_price,
        prepay          = prepay,
        pending         = pending,
        driver          = driver,
        return_pickup_date   = return_date_obj if has_return else None,
        return_flight_number = return_flight_number if has_return else '',
        return_flight_time   = return_flight_time if has_return else '',
        return_pickup_time   = return_pickup_time if has_return else '',
        # 지점간 예약의 돌아오는 편은 공항 방향이 아니라 출발/도착지를 뒤집은 것이다.
        return_direction     = '' if (is_point_to_point or not has_return) else 'Pickup from Intl Airport',
        return_start_point   = end_point if (has_return and is_point_to_point) else '',
        return_end_point     = start_point if (has_return and is_point_to_point) else '',
        extra_stop           = extra_stop,
        same_extra_stop      = same_extra_stop,
        extra_stop_addresses = extra_stop_addresses,
        special_items        = special_items,
    )
    logger.debug(
        "[QUICK REBOOK] pre-save street=%r (from Post id=%s, email=%s)",
        previous_street, previous.id, email,
    )
    p.save()


    logger.info(f"[QUICK REBOOK CONFIRM] Post id={p.id} email={email} date={pickup_date_str}")

    ip      = get_client_ip(request)
    ip_info = get_ip_info(ip)
    try:
        asyncio.run(send_telegram_notification(
            f"🔄 Quick Rebook:\n"
            f"IP: `{ip}`\n"
            f"Location: {ip_info}"
        ))
    except Exception as e:
        logger.error(f"[TELEGRAM] Quick Rebook failed: {e}")

    return booking_success_response(request)