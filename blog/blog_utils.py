import logging

from django.utils import timezone
from django.db.models import Q
from main.settings import DEFAULT_FROM_EMAIL
from basecamp.basecamp_utils import render_email_template
from blog.models import Driver, Post
from regions.models import RegionSuburb
from utils.email import send_text_email, send_html_email
from utils.telegram import send_telegram_sync


logger = logging.getLogger('easygo')


def clean_float(value):
    try:
        return "{:.2f}".format(float(value)).rstrip('0').rstrip('.')
    except (ValueError, TypeError):
        return "0"


def _net_adjustment(post):
    """Return (surcharge, discount) numeric adjustments from a booking's own
    fields, mirroring basecamp.views.payments._calc_surcharge / _calc_discount
    when called with no form input (the charge-side fallback). Only numeric
    field values are applied; blank or text values (e.g. "surcharge included"
    on self-booked Posts whose price is already all-inclusive) yield 0 so the
    reconciled amount matches what was charged."""
    s = (getattr(post, 'surcharge', '') or '').strip()
    surcharge = round(float(s), 2) if s.replace('.', '', 1).isdigit() else 0.0
    d = (getattr(post, 'discount', '') or '').strip()
    discount = float(d) if d.replace('.', '', 1).isdigit() else 0.0
    return surcharge, discount


def process_generic_payment(payment_instance, posts, admin_email, calculated_amount=None):
    """
    Stripe/PayPal 결제 건을 분석하여 여러 예약(Post)에 금액을 배분합니다.
    """
    instance = payment_instance

    if instance.is_processed:
        txn_id = getattr(instance, 'payment_intent_id', getattr(instance, 'txn_id', 'N/A'))
        method = "STRIPE" if hasattr(instance, 'payment_intent_id') else "PAYPAL"
        
        admin_notice = f'''
        ⚠️ 중복 결제 처리 시도 감지 (차단됨)
        시스템이 이미 처리된 결제 건을 다시 처리하려는 시도를 막았습니다.

        - 이름: {instance.name}
        - 이메일: {instance.email}
        - 금액: ${calculated_amount if calculated_amount is not None else instance.amount}
        - 결제수단: {method}
        - 거래ID: {txn_id}
        - 최초처리일: {instance.processed_at}
        '''
        send_text_email(
            subject=f"⚠️ [Duplicate] {instance.name} - {method}",
            message=admin_notice,
            recipient_list=[admin_email],
        )
        return False, 0.0, set(), False, False, False

    posts = posts.filter(
        pickup_date__isnull=False,
        pickup_date__gte=timezone.localdate(),
    )
    posts_list = list(posts)
    has_future_bookings = bool(posts_list)

    total_balance = 0.0
    for post in posts_list:
        try:
            surcharge, discount = _net_adjustment(post)
            balance = round(float(post.price or 0) + surcharge - discount - float(post.paid or 0), 2)
        except (ValueError, TypeError):
            continue
        if balance > 0:
            total_balance += balance

    all_already_paid = has_future_bookings and total_balance == 0
    remaining_amount = float(calculated_amount or instance.amount or 0)
    recipient_emails = set()
    method_label = "STRIPE" if hasattr(instance, 'payment_intent_id') else "PAYPAL"

    for post in posts_list:
        if remaining_amount <= 0:
            break

        try:
            p_price = float(post.price or 0)
            p_paid = float(post.paid or 0)
        except (ValueError, TypeError):
            continue

        surcharge, discount = _net_adjustment(post)
        p_total = round(p_price + surcharge - discount, 2)
        balance = round(p_total - p_paid, 2)
        if balance <= 0:
            continue

        apply_now = min(remaining_amount, balance)
        total_balance -= apply_now

        new_paid = p_paid + apply_now
        post.paid = clean_float(new_paid)
        post.toll = "" if new_paid >= p_total else "short payment"
        post.reminder = True
        post.pending = False
        post.cancelled = False

        new_entry = f"{method_label}: ${apply_now:.0f}"
        post.notice = f"{post.notice or ''} | {new_entry}".strip(" | ")

        post.save()
        remaining_amount -= apply_now
        if post.booker_email:
            recipient_emails.add(post.booker_email)
        else:
            recipient_emails.update(filter(None, [post.email, post.email1]))

    instance.is_processed = True
    instance.processed_at = timezone.now()
    instance.save()

    # 남은 잔액(total_balance > 0)이 전부 "디파짓 인보이스로 이미 예고된 미납분"으로
    # 설명되면 미납 안내 메일을 보낼 필요가 없음. 디파짓 문턱(deposit_amount_due)을
    # 아직 못 채운 post가 하나라도 있으면 진짜 부족 결제이므로 그대로 경고 메일 발송.
    deposit_satisfied = False
    if total_balance > 0:
        deposit_satisfied = True
        for post in posts_list:
            try:
                surcharge, discount = _net_adjustment(post)
                p_total = round(float(post.price or 0) + surcharge - discount, 2)
                p_paid = float(post.paid or 0)
            except (ValueError, TypeError):
                continue
            if round(p_total - p_paid, 2) <= 0:
                continue
            deposit_due = post.deposit_amount_due
            if deposit_due is None or p_paid < float(deposit_due):
                deposit_satisfied = False
                break

    return True, total_balance, recipient_emails, has_future_bookings, all_already_paid, deposit_satisfied


def send_payment_notification_email(instance, total_balance, recipient_emails, admin_email, method, raw_amount=None, net_amount=None, booker_name=None, has_future_bookings=False, all_already_paid=False, nearest_post=None, deposit_satisfied=False):
    if net_amount is None:
        net_amount = float(instance.amount or 0)
    if raw_amount is None:
        raw_amount = net_amount

    remaining_balance = round(total_balance, 2)

    # ✅ 고객에게만 이메일 (admin_email 제거)
    recipient_list = [email for email in recipient_emails if email]

    if total_balance == 0 and instance.email and instance.email not in recipient_list:
        recipient_list.append(instance.email)

    context = {
        'name': instance.name,
        'booker_name': booker_name,
        'email': instance.email,
        'raw_amount': raw_amount,
        'amount': net_amount,
    }

    if not has_future_bookings:
        template = "html_email-noIdentity.html" if method == "PAYPAL" else "html_email-noIdentity-stripe.html"
    elif all_already_paid or remaining_balance <= 0:
        template = "html_email-payment-success.html" if method == "PAYPAL" else "html_email-payment-success-stripe.html"
    elif deposit_satisfied:
        # 디파짓 인보이스로 예고된 부분 결제 — 잔액이 남아도 미납 경고 메일은 보내지 않음.
        template = None
    else:
        template = "html_email-response-discrepancy.html"
        context.update({
            'price': round(net_amount + total_balance, 2),
            'paid': round(net_amount, 2),
            'diff': round(remaining_balance, 2)
        })

    if template:
        html_content = render_email_template(template, context)
        send_html_email("Payment Received - EasyGo", html_content, recipient_list, from_email=DEFAULT_FROM_EMAIL)

    amount_display = f"${raw_amount} (${net_amount})" if raw_amount != net_amount else f"${net_amount}"

    if deposit_satisfied:
        send_telegram_sync(
            f"💰 Deposit payment received via {method}\n\n"
            f"👤 {instance.name}\n"
            f"📧 {instance.email}\n"
            f"💰 ${net_amount} (remaining balance: ${remaining_balance})"
        )
    elif all_already_paid:
        if nearest_post:
            entry = f"paid again ${raw_amount} via {method.capitalize()}"
            nearest_post.notice = f"{nearest_post.notice or ''} | {entry}".strip(" | ")
            nearest_post.save()
        send_telegram_sync(
            f"Fully paid but paid again {method.capitalize()}: {amount_display}\n"
            f"👤 {instance.name}\n"
            f"📧 {instance.email}"
        )
    elif not has_future_bookings:
        send_telegram_sync(
            f"No future bookings found. Manual action required.\n"
            f"👤 {instance.name}\n"
            f"📧 {instance.email}\n"
            f"{method.capitalize()}: {amount_display}"
        )
    else:
        send_telegram_sync(
            f"💳 Payment received via {method}\n\n"
            f"👤 {instance.name}\n"
            f"📧 {instance.email}\n"
            f"💰 ${net_amount}"
        )
    
   
def get_default_driver_for_region(region):
    return Driver.objects.filter(
        region=region,
        is_default=True
    ).first()


def resolve_driver(suburb):
    if not suburb:
        logger.warning("resolve_driver called with empty suburb")
        return None

    suburb_obj = RegionSuburb.objects.filter(Q(slug=suburb.lower()) | Q(name__iexact=suburb)).first()

    if not suburb_obj:
        logger.warning(f"No suburb found for value '{suburb}'")
        return None

    driver = get_default_driver_for_region(suburb_obj.region)

    if driver: 
        return driver

    else:
        logger.warning(
            f"No default driver for region '{suburb_obj.region.name}' "
            f"(suburb: '{suburb}')"
        )

    return Driver.objects.filter(is_default=True).first()