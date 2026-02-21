import re
import requests
import stripe

from datetime import datetime, date
from io import BytesIO

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, send_mail
from django.utils.html import strip_tags
from basecamp.area_home import get_home_suburbs
from main import settings
from weasyprint import HTML
from blog.models import StripePayment


# 이메일 템플릿 최상위 경로
EMAIL_TEMPLATE_BASE = "basecamp/emails/html_email/"

def render_email_template(template_name, context, request=None):
    if not template_name.startswith("basecamp/emails/html_email/"):
        template_name = f"{EMAIL_TEMPLATE_BASE}{template_name}"

    return render_to_string(template_name, context, request=request)

# --------------------------
# Cloudflare Turnstile
# --------------------------
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


# --------------------------
# PDF 렌더링
# --------------------------
def render_to_pdf(template_src, context_dict={}):
    html_string = render_email_template(template_src, context_dict)
    html = HTML(string=html_string, base_url=None)  # base_url 설정 가능
    result = BytesIO()
    html.write_pdf(target=result)
    return result.getvalue()


# --------------------------
# Date parsing
# --------------------------
def parse_date(date_str, field_name="Date", required=True, reference_date=None):

    # ✅ 이미 datetime.date 타입이면 그대로 반환
    if isinstance(date_str, date):
        return date_str

    # ✅ None 또는 빈 문자열 체크
    if not date_str or str(date_str).strip() == "":
        if required:
            raise ValueError(f"'{field_name}' is a required field.")
        return None

    # ✅ 문자열 -> datetime 변환
    try:
        parsed_date = datetime.strptime(str(date_str), '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid date format for '{field_name}' ({date_str}). Please use YYYY-MM-DD.")

    # ✅ 오늘 날짜보다 미래인지 확인
    if parsed_date <= date.today():
        raise ValueError(f"'{field_name}' cannot be in the past ({date.today().strftime('%Y-%m-%d')}).")

    # ✅ 기준 날짜(reference_date)보다 빠른지 확인
    if reference_date and parsed_date < reference_date:
        ref_str = reference_date.strftime('%Y-%m-%d')
        raise ValueError(f"'{field_name}' ({parsed_date}) cannot be before the initial pickup date ({ref_str}).")

    return parsed_date


# --------------------------
# Email sending
# --------------------------
def handle_email_sending(request, email, subject, template_name, context, email1=None):

    html_content = render_email_template(template_name, context, request=request)
    text_content = strip_tags(html_content)
    
    recipient_list = [email, settings.RECIPIENT_EMAIL]

    if email1:  
        recipient_list.append(email1)
    
    email_message = EmailMultiAlternatives(
        subject,
        text_content,
        '',
        recipient_list,
    )
    email_message.attach_alternative(html_content, "text/html; charset=UTF-8")
    email_message.encoding = 'utf-8'

    # (선택) 메일 헤더에 charset 명시 — Outlook 호환성 향상
    email_message.extra_headers = {
        'Content-Type': 'text/html; charset=UTF-8',
        'Content-Transfer-Encoding': '8bit',
    }

    email_message.send()


def format_pickup_time_12h(pickup_time_str):
    try:
        time_obj = datetime.strptime(pickup_time_str.strip(), "%H:%M")
        return time_obj.strftime("%I:%M %p")  # 예: "06:30 PM"
    except ValueError:
        return pickup_time_str  # 실패 시 원래 값 반환
    

# --------------------------
# Missing info email
# --------------------------
def check_and_send_missing_info_email(post):
    issues = []

    # ---------- CONTACT CHECK ----------
    contact = (post.contact or '').strip()
    cleaned_contact = ''.join(filter(str.isdigit, contact))
    if not cleaned_contact or len(cleaned_contact) < 10 or len(cleaned_contact) > 16:
        issues.append('Contact number is missing or invalid')

    # ---------- FLIGHT CHECK ----------
    AIRPORT_PICKUPS = {
        'pickup from intl airport',
        'pickup from domestic airport',
    }

    flight_number = (post.flight_number or '').strip()
    flight_number_cleaned = re.sub(r'[^A-Za-z0-9]', '', flight_number).upper()

    flight_issue = False

    if post.direction and post.direction.strip().lower() in AIRPORT_PICKUPS:

        flight_valid = False

        # 특별 예외: '5j39'
        if flight_number_cleaned.lower() == '5j39':
            flight_valid = True
        else:
            match = re.match(r'^([A-Z]{1,3})(\d+)$', flight_number_cleaned)
            if match:
                number_part_raw = match.group(2)
                number_part_no_zero = number_part_raw.lstrip('0')
                if len(number_part_no_zero) <= 4:
                    flight_valid = True

        if not flight_valid:
            flight_issue = True
            issues.append('Flight number is missing or invalid')

    # ---------- SEND EMAIL ----------
    if issues:
        handle_email_sending(
            request=None,
            email=post.email,
            subject="Missing or Invalid Flight/Contact Information Reminder",
            template_name="html_email-missing-flight-contact.html",
            context={
                'name': post.name,
                'email': post.email,
                'pickup_date': post.pickup_date,
                'direction': post.direction,
                'flight_number': post.flight_number,
                'contact': post.contact,
                'issues': issues,
            }
        )

# --------------------------
# Utility
# --------------------------
def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def add_bag(summary_list, label, qty, oversize=False):
    """
    summary_list : list
    label        : str (L, M, Ski, Bike 등)
    qty          : int
    oversize     : bool
    """
    if qty and qty > 0:
        item = f"{label}{qty}"
        if oversize:
            item += "(Oversize)"
        summary_list.append(item)


def to_bool(value):
    return str(value).lower() in ["true", "1", "on", "yes"]


# 안전한 float 변환 함수 (inc toll 같은 것도 처리)
def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        if value and 'inc' in value.lower():
            return 0.0
        return None


# --------------------------
# PayPal error email
# --------------------------
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


# --------------------------
# Stripe handling
# --------------------------
stripe.api_key = settings.STRIPE_LIVE_SECRET_KEY

def handle_checkout_session_completed(session):
    email = session.customer_details.email
    name = session.customer_details.name
    amount = session.amount_total / 100
    payment_intent_id = session.payment_intent or session.id

    try:
        payment, created = StripePayment.objects.update_or_create(
            payment_intent_id=payment_intent_id,
            defaults={
                "name": name,
                "email": email,
                "amount": amount,
            }
        )
        print(f"StripePayment saved. created={created}")

    except Exception as e:
        stripe_payment_error_email(
            'Stripe Payment Save Error',
            str(e),
            name,
            email,
            amount
        )


def stripe_payment_error_email(subject, message, name, email, amount):
    content = f"""
    Subject: {subject}
    
    Error: {message}
    Name: {name}
    Email: {email}
    Amount: {amount}
    """

    send_mail(
        subject=subject,
        message=content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.RECIPIENT_EMAIL],
    )

# --------------------------
# get_sorted_suburbs
# --------------------------
def get_sorted_suburbs():
    raw = get_home_suburbs()
    fixed = [
        "Hotels In City",  
        "Sydney Int'l Airport",
        "Sydney Domestic Airport",
        "WhiteBay cruise terminal",
        "Overseas cruise terminal"
    ]
    remaining = sorted([item for item in raw if item not in fixed])
    return fixed + remaining