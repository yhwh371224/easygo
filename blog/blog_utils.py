import logging
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings
from main.settings import RECIPIENT_EMAIL, DEFAULT_FROM_EMAIL
from basecamp.basecamp_utils import render_email_template

logger = logging.getLogger('easygo')


def payment_send_email(subject, html_content, recipient_list):
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        subject,
        text_content,
        DEFAULT_FROM_EMAIL,
        recipient_list
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


def clean_float(value):
    try:
        return "{:.2f}".format(float(value)).rstrip('0').rstrip('.')
    except (ValueError, TypeError):
        return "0"


def process_generic_payment(payment_instance, posts, recipient_email_config):
    """
    Stripe/PayPal 결제 건을 분석하여 여러 예약(Post)에 금액을 배분합니다.
    """
    instance = payment_instance
    admin_email = RECIPIENT_EMAIL

    if instance.is_processed:
        txn_id = getattr(instance, 'payment_intent_id', getattr(instance, 'txn_id', 'N/A'))
        method = "STRIPE" if hasattr(instance, 'payment_intent_id') else "PAYPAL"
        
        admin_notice = f'''
        ⚠️ 중복 결제 처리 시도 감지 (차단됨)
        시스템이 이미 처리된 결제 건을 다시 처리하려는 시도를 막았습니다.

        - 이름: {instance.name}
        - 이메일: {instance.email}
        - 금액: ${instance.amount}
        - 결제수단: {method}
        - 거래ID: {txn_id}
        - 최초처리일: {instance.processed_at}
        '''
        send_mail(
            subject=f"⚠️ [Duplicate] {instance.name} - {method}",
            message=admin_notice,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
        )
        return False, 0.0, set()

    remaining_amount = float(instance.amount or 0)
    total_balance = 0.0
    recipient_emails = set()
    method_label = "STRIPE" if hasattr(instance, 'payment_intent_id') else "PAYPAL"

    for post in posts:
        if remaining_amount <= 0:
            break
            
        try:
            p_price = float(post.price or 0)
            p_paid = float(post.paid or 0)
        except (ValueError, TypeError):
            continue

        balance = round(p_price - p_paid, 2)
        if balance <= 0:
            continue
        
        total_balance += balance
        apply_now = min(remaining_amount, balance)
        
        # 실제 데이터 업데이트
        new_paid = p_paid + apply_now
        post.paid = clean_float(new_paid)
        post.toll = "" if new_paid >= p_price else "short payment"
        post.cash = False
        post.reminder = True
        post.pending = False
        post.cancelled = False
        
        new_entry = f"==={method_label}=== paid: ${apply_now:.2f}"
        post.notice = f"{post.notice or ''} | {new_entry}".strip(" | ")
        
        post.save()
        remaining_amount -= apply_now
        recipient_emails.update([post.email, post.email1])

    instance.is_processed = True
    instance.processed_at = timezone.now()
    instance.save()

    return True, total_balance, recipient_emails


def send_payment_notification_email(instance, total_balance, recipient_emails, admin_email, method, raw_amount=None, net_amount=None):
    """
    Stripe/PayPal 각각의 템플릿과 금액을 처리합니다.
    """
    if net_amount is None:
        net_amount = float(instance.amount or 0)
    if raw_amount is None:
        raw_amount = net_amount

    remaining_balance = round(total_balance - net_amount, 2)
    recipient_list = [email for email in recipient_emails if email] + [admin_email]

    context = {
        'name': instance.name,
        'email': instance.email,
        'raw_amount': raw_amount,  
        'amount': net_amount,     
    }

    if total_balance == 0:
        if method == "PAYPAL":
            template = "html_email-noIdentity.html" 
        else:
            template = "html_email-noIdentity-stripe.html"
    elif remaining_balance <= 0:
        if method == "PAYPAL":
            template = "html_email-payment-success.html"
        else:
            template = "html_email-payment-success-stripe.html"
    else:
        template = "html_email-response-discrepancy.html"
        context.update({
            'price': round(total_balance, 2),
            'paid': round(net_amount, 2),
            'diff': round(remaining_balance, 2)
        })

    html_content = render_email_template(template, context)
    payment_send_email("Payment Received - EasyGo", html_content, recipient_list)