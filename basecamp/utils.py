from datetime import datetime, date
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings

from django.template.loader import render_to_string
from weasyprint import HTML
from io import BytesIO


ADMIN_EMAIL = getattr(settings, 'RECIPIENT_EMAIL', 'info@easygoshuttle.com.au') 
SENDER_EMAIL = getattr(settings, 'SENDER_EMAIL', ADMIN_EMAIL) 


def render_to_pdf(template_src, context_dict={}):
    html_string = render_to_string(template_src, context_dict)
    html = HTML(string=html_string, base_url=None)  # base_url 설정 가능
    result = BytesIO()
    html.write_pdf(target=result)
    return result.getvalue()


def parse_date(date_str, field_name="Date", required=True, reference_date=None):

    if not date_str or date_str.strip() == "":
        if required:
            raise ValueError(f"'{field_name}' is a required field.")
        return None

    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid date format for '{field_name}' ({date_str}). Please use YYYY-MM-DD.")

    if parsed_date <= date.today():
        raise ValueError(f"'{field_name}' must be a date after today ({date.today().strftime('%Y-%m-%d')}).")
        
    if reference_date and parsed_date < reference_date:
        ref_str = reference_date.strftime('%Y-%m-%d')
        raise ValueError(f"'{field_name}' ({parsed_date}) cannot be before the initial pickup date ({ref_str}).")

    return parsed_date


# email_dispatch_detail 
def handle_email_sending(request, email, subject, template_name, context, email1=None):
    html_content = render_to_string(template_name, context, request=request)
    text_content = strip_tags(html_content)
    text_content = text_content.replace('✅', '').replace('🚨', '').replace('💰', '')
    
    recipient_list = [email, ADMIN_EMAIL]

    if email1:  # email1이 제공되었을 경우 추가
        recipient_list.append(email1)
    
    email_message = EmailMultiAlternatives(
        subject,
        text_content,
        f"EasyGo Airport Shuttle <{SENDER_EMAIL}>",
        recipient_list,
    )
    email_message.attach_alternative(html_content, "text/html")

    email_message.send()


def format_pickup_time_12h(pickup_time_str):
    try:
        time_obj = datetime.strptime(pickup_time_str.strip(), "%H:%M")
        return time_obj.strftime("%I:%M %p")  # 예: "06:30 PM"
    except ValueError:
        return pickup_time_str  # 실패 시 원래 값 반환
    

