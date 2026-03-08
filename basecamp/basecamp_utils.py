import re

from io import BytesIO

from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from main import settings
from weasyprint import HTML

# --------------------------
# Re-exports (하위호환 유지)
# --------------------------
from basecamp.modules.view_helpers import (   # noqa: F401
    verify_turnstile,
    is_ajax,
    render_inquiry_done,
    booking_success_response,
    require_turnstile,
    is_duplicate_submission,
    get_customer_status,
    parse_one_based_index,
    resolve_payment_flags,
)
from basecamp.modules.date_utils import (      # noqa: F401
    parse_date,
    parse_booking_dates,
    format_pickup_time_12h,
)
from basecamp.modules.baggage_utils import (   # noqa: F401
    to_int,
    to_bool,
    add_bag,
    safe_float,
    parse_baggage,
)
from basecamp.modules.payment_utils import (   # noqa: F401
    paypal_ipn_error_email,
    handle_checkout_session_completed,
    stripe_payment_error_email,
)
from basecamp.modules.suburb_utils import (    # noqa: F401
    get_sorted_suburbs,
)


# --------------------------
# 이메일 템플릿 렌더링
# --------------------------
EMAIL_TEMPLATE_BASE = "basecamp/email/html_email/"

def render_email_template(template_name, context, request=None):
    if not template_name.startswith("basecamp/email/html_email/"):
        template_name = f"{EMAIL_TEMPLATE_BASE}{template_name}"
    return render_to_string(template_name, context, request=request)


# --------------------------
# PDF 렌더링
# --------------------------
def render_to_pdf(template_src, context_dict={}):
    html_string = render_email_template(template_src, context_dict)
    html = HTML(string=html_string, base_url=None)
    result = BytesIO()
    html.write_pdf(target=result)
    return result.getvalue()


# --------------------------
# Email sending (Outlook 호환 헤더 포함)
# --------------------------
def handle_email_sending(request, email, subject, template_name, context, email1=None):
    now = timezone.localtime(timezone.now()).strftime("%d %b %H:%M")
    subject = f"{subject} (sent {now})"
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
    email_message.extra_headers = {
        'Content-Type': 'text/html; charset=UTF-8',
        'Content-Transfer-Encoding': '8bit',
    }
    email_message.send()


# --------------------------
# Missing info email
# --------------------------
def check_and_send_missing_info_email(post):
    issues = []

    contact = (post.contact or '').strip()
    cleaned_contact = ''.join(filter(str.isdigit, contact))
    if not cleaned_contact or len(cleaned_contact) < 10 or len(cleaned_contact) > 16:
        issues.append('Contact number is missing or invalid')

    AIRPORT_PICKUPS = {
        'pickup from intl airport',
        'pickup from domestic airport',
    }

    flight_number = (post.flight_number or '').strip()
    flight_number_cleaned = re.sub(r'[^A-Za-z0-9]', '', flight_number).upper()

    if post.direction and post.direction.strip().lower() in AIRPORT_PICKUPS:
        flight_valid = False

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
            issues.append('Flight number is missing or invalid')

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
