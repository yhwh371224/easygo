from main.settings import RECIPIENT_EMAIL
from basecamp.basecamp_utils import render_email_template
from utils.email import send_html_email
import re
from decimal import Decimal

from django.utils import timezone

from utils.direction_utils import arrival_type


def _safe_decimal(value):
    """paid is a free-text CharField (may be blank/None/'TBA') — parse defensively."""
    try:
        return Decimal(str(value)) if value not in (None, '', 'TBA') else Decimal(0)
    except Exception:
        return Decimal(0)


def _find_return_leg(instance):
    """Find the sibling Post created by handle_return_trip() for the return leg.

    handle_return_trip() splits a round-trip booking into two Post rows (each
    holding its own half of price/paid) rather than linking them by FK, so we
    match on the fields it sets: same email, return_pickup_time == "x", and
    pickup/return dates swapped relative to this (outbound) instance.
    """
    from blog.models import Post

    if not instance.return_pickup_time or instance.return_pickup_time == 'x':
        return None

    return Post.objects.filter(
        email=instance.email,
        return_pickup_time='x',
        pickup_date=instance.return_pickup_date,
        return_pickup_date=instance.pickup_date,
    ).exclude(pk=instance.pk).order_by('-pk').first()


def send_post_confirmation_email(instance):
    subject = "Booking Confirmation - EasyGo"

    paid_total = instance.paid

    if instance.price not in [None, "TBA", ""]:
        if instance.return_pickup_time:
            return_leg = _find_return_leg(instance)
            if return_leg is not None and return_leg.price not in [None, "TBA", ""]:
                # Sum the two actual split rows rather than assuming an exact
                # 50/50 split (paid amounts can be adjusted per-leg later).
                price = int(Decimal(instance.price) + Decimal(return_leg.price))
                paid_total = _safe_decimal(instance.paid) + _safe_decimal(return_leg.paid)
            else:
                price = int(Decimal(instance.price) * 2)
                paid_total = _safe_decimal(instance.paid) * 2
        else:
            price = int(Decimal(instance.price))
    else:
        price = "TBA"

    raw_discount = str(instance.discount or '').strip()
    try:
        discount_amount = int(Decimal(raw_discount)) if raw_discount else 0
    except Exception:
        discount_amount = 0

    raw_surcharge = str(instance.surcharge or '').strip()
    try:
        surcharge_amount = int(Decimal(raw_surcharge)) if raw_surcharge else 0
    except Exception:
        surcharge_amount = 0

    try:
        final_price = (
            int(Decimal(str(price)) - discount_amount + surcharge_amount)
            if isinstance(price, int) and (discount_amount or surcharge_amount)
            else price
        )
    except Exception:
        final_price = price

    html_content = render_email_template(
        "html_email-confirmation.html",
        {
        'booker_name': instance.booker_name,
        'booker_email': instance.booker_email,
        'booker_contact': instance.booker_contact,
        'company_name': instance.company_name,
        'name': instance.name,
        'contact': instance.contact,
        'email': instance.email,
        'email1': instance.email1,

        'pickup_date': instance.pickup_date,
        'flight_number': instance.flight_number,
        'flight_time': instance.flight_time,
        'pickup_time': instance.pickup_time,

        'direction': instance.direction,
        'street': instance.street,
        'suburb': instance.suburb,
        'start_point': instance.start_point,
        'end_point': instance.end_point,

        'no_of_passenger': instance.no_of_passenger,
        'no_of_baggage': instance.no_of_baggage,

        # return trip
        'return_direction': instance.return_direction,
        'return_pickup_date': instance.return_pickup_date,
        'return_flight_number': instance.return_flight_number,
        'return_flight_time': instance.return_flight_time,
        'return_no_of_passenger': instance.return_no_of_passenger,
        'return_pickup_time': instance.return_pickup_time,
        'return_start_point': instance.return_start_point,
        'return_end_point': instance.return_end_point,

        'message': instance.message,
        'notice': instance.notice,
        'reminder': instance.reminder,

        # payment
        'price': price,
        'paid': paid_total,
        'cash': instance.cash,
        'prepay': instance.prepay,

        # extra
        'toll': instance.toll,
        'surcharge': surcharge_amount,
        'extra_stop_addresses': instance.extra_stop_addresses or [],
        'same_extra_stop': instance.same_extra_stop,
        'discount': discount_amount,
        'final_price': final_price,
        }
    )

    customer_recipients = [instance.booker_email] if instance.booker_email else list(filter(None, [instance.email, instance.email1]))
    recipients = customer_recipients + [RECIPIENT_EMAIL]
    send_html_email(subject, html_content, recipients)


def arrival_legs(instance):
    """이 부킹(왕복이면 리턴 편 포함) 중 비행기 도착 픽업인 구간 목록.

    왕복은 handle_return_trip() 이 리턴 편을 별도 Post(return_pickup_time='x')로
    쪼개지만, 컨펌 메일은 원래 행에 return_* 필드를 담아 한 번에 나가므로 여기서도
    원래 행의 return_* 를 보고 리턴 편 도착 여부를 판단한다. 'x' 행 자체는 자기
    direction 이 곧 리턴 편 방향이라 그 구간만 본다.
    """
    from utils.booking_helper import reverse_direction

    legs = []
    if arrival_type(instance.direction, instance.start_point):
        legs.append({
            'label': 'Arrival',
            'date': instance.pickup_date,
            'flight_number': instance.flight_number,
            'flight_time': instance.flight_time,
        })

    has_return = instance.return_pickup_time and instance.return_pickup_time != 'x'
    if has_return:
        return_dir = instance.return_direction or reverse_direction(instance.direction)
        if arrival_type(return_dir, instance.return_start_point):
            legs.append({
                'label': 'Return arrival' if legs else 'Arrival (return trip)',
                'date': instance.return_pickup_date,
                'flight_number': instance.return_flight_number,
                'flight_time': instance.return_flight_time,
            })
    return legs


def _arrival_guide_steps(region):
    """Region.arrival_guide(줄마다 '1. 제목 - 내용') 를 메일용 [{title, body}] 로 바꾼다."""
    steps = []
    for line in (getattr(region, 'arrival_guide', '') or '').splitlines():
        line = re.sub(r'^\s*\d+\s*[.)]\s*', '', line.strip())
        if not line:
            continue
        title, sep, body = line.partition(' - ')
        steps.append({'title': title.strip(), 'body': body.strip()} if sep else {'title': '', 'body': line})
    return steps


def send_arrival_guide_email(instance):
    """비행기 도착 구간이 있는 부킹에 지역별 Arrival Guide 를 안내하는 메일.

    컨펌 메일 직후 send_arrival_guide_email_task 가 부른다. 보낼 게 없으면
    (도착 구간 없음/취소/도착일이 모두 지남) False 를 돌려준다.
    """
    from regions.models import Region

    if instance.cancelled:
        return False

    today = timezone.localdate()
    legs = [leg for leg in arrival_legs(instance) if not leg['date'] or leg['date'] >= today]
    if not legs:
        return False

    region = instance.region if instance.region_id else Region.objects.filter(slug='sydney').first()
    # 미팅 장소(meeting-point / arrival-guide 페이지) 링크는 넣지 않는다. 미리 보면 손님이
    # 그곳이 자기 장소인 줄 알고 가버린다 — 실제 장소는 도착 후 리마인더 메일로만 안내한다.
    html_content = render_email_template("html_email-arrival-guide.html", {
        'booker_name': instance.booker_name,
        'name': instance.name,
        'email': instance.email,
        'legs': legs,
        'city': region.name if region else 'Sydney',
        'steps': _arrival_guide_steps(region),
    })

    customer_recipients = [instance.booker_email] if instance.booker_email else list(filter(None, [instance.email, instance.email1]))
    if not customer_recipients:
        return False
    send_html_email("Your Airport Arrival Guide - EasyGo", html_content, customer_recipients + [RECIPIENT_EMAIL])
    return True


def send_post_cancelled_email(instance, unpaid_balance=None, amount_paid=None, non_payment=False):
    """부킹 취소 통보 메일.

    unpaid_balance/amount_paid 는 부분결제(short payment) 미납으로 자동취소된
    건에서만 넘어온다(auto_cancel_pending). 값이 있으면 이미 결제된 금액이
    있다는 사실을 메일에 명시해 손님이 환불 문의를 어디로 해야 할지 알게 한다.
    일반 취소(가용 차량 없음 등)에서는 None 이라 문구가 나오지 않는다.

    non_payment=True 는 final notice 발송 후에도 응답/결제가 없어 자동취소된
    건(auto_cancel_pending)에서만 넘어온다. 이 경우 "여러 차례 안내했지만
    응답/결제가 없어 취소한다"는 문구의 전용 템플릿을 사용한다.
    """
    template = "html_email-cancelled-nonpayment.html" if non_payment else "html_email-cancelled.html"
    html_content = render_email_template(template, {
        'booker_name': instance.booker_name,
        'booker_email': instance.booker_email,
        'booker_contact': instance.booker_contact,
        'name': instance.name,
        'email': instance.email,
        'pickup_date': instance.pickup_date,
        'pickup_time': instance.pickup_time,
        'return_pickup_date': instance.return_pickup_date,
        'return_pickup_time': instance.return_pickup_time,
        'unpaid_balance': unpaid_balance,
        'amount_paid': amount_paid,
    })
    
    recipients = [instance.booker_email] if instance.booker_email else list(filter(None, [instance.email, instance.email1]))
    send_html_email("EasyGo Booking Cancelled", html_content, recipients)


def send_missing_direction_email(instance):
    subject = "Booking with Flight Number but Missing Direction"
    template = "html_email-missing-flight-contact.html"

    html_content = render_email_template(template, {
        'booker_name': instance.booker_name,
        'booker_email': instance.booker_email,
        'booker_contact': instance.booker_contact,
        'name': instance.name,
        'email': instance.email,
        'pickup_date': instance.pickup_date,
        'flight_number': instance.flight_number,
        'issues': ['Direction is missing or not specified'],
    })

    send_html_email(subject, html_content, [RECIPIENT_EMAIL])