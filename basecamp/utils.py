from datetime import datetime, date
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from main.settings import RECIPIENT_EMAIL

from django.template.loader import render_to_string
from weasyprint import HTML
from io import BytesIO


def render_to_pdf(template_src, context_dict={}):
    html_string = render_to_string(template_src, context_dict)
    html = HTML(string=html_string, base_url=None)  # base_url 설정 가능
    result = BytesIO()
    html.write_pdf(target=result)
    return result.getvalue()


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
    if parsed_date < date.today():
        raise ValueError(f"'{field_name}' cannot be in the past ({date.today().strftime('%Y-%m-%d')}).")

    # ✅ 기준 날짜(reference_date)보다 빠른지 확인
    if reference_date and parsed_date < reference_date:
        ref_str = reference_date.strftime('%Y-%m-%d')
        raise ValueError(f"'{field_name}' ({parsed_date}) cannot be before the initial pickup date ({ref_str}).")

    return parsed_date



# email_dispatch_detail 
def handle_email_sending(request, email, subject, template_name, context, email1=None):

    html_content = render_to_string(template_name, context, request=request)
    text_content = strip_tags(html_content)
    
    recipient_list = [email, RECIPIENT_EMAIL]

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
    

