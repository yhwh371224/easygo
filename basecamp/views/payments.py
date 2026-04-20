from datetime import datetime, date
import requests
import stripe
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from main.settings import RECIPIENT_EMAIL
from utils.email import send_html_email
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from blog.models import Post, PaypalPayment
from basecamp.basecamp_utils import (
    render_to_pdf, safe_float,
    handle_checkout_session_completed, paypal_ipn_error_email,
    verify_turnstile, render_email_template,
    render_inquiry_done, require_turnstile, parse_one_based_index,
    is_ajax,
)
from django_ratelimit.decorators import ratelimit


# ---------------------------------------------------------------------------
# Invoice helpers
# ---------------------------------------------------------------------------

def _parse_invoice_params(request):
    """Extract and normalize all POST parameters for invoice generation."""
    return {
        'email': request.POST.get('email', '').strip(),
        'apply_gst_flag': request.POST.get('apply_gst'),
        'surcharge_input': request.POST.get('surcharge'),
        'discount_input': request.POST.get('discount'),
        'inv_no': request.POST.get('inv_no'),
        'toll_input': request.POST.get('toll'),
        'index': request.POST.get('index', '1'),
        'from_date': request.POST.get('from_date'),
        'to_date': request.POST.get('to_date'),
    }


def _resolve_inv_no(user, inv_no_raw):
    """Return the invoice number, falling back to pickup_date ordinal."""
    if inv_no_raw and inv_no_raw.strip():
        return inv_no_raw.strip()
    return f"{user.pickup_date.toordinal()}" if user.pickup_date else "896021"


def _resolve_bookings(users, index, from_date, to_date):
    """Return (bookings, is_multiple)."""
    if from_date and to_date:
        from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
        bookings = users.filter(
            pickup_date__range=(from_date_obj, to_date_obj)
        ).order_by('pickup_date', 'pickup_time')
        return bookings, True
    bookings = [users[index]] if 0 <= index < len(users) else [users.first()]
    return bookings, False


def _calc_surcharge(surcharge_input, price):
    """Return (surcharge_calc, surcharge_display)."""
    if surcharge_input == "Yes":
        calc = round(price * 0.03, 2)
        return calc, calc
    if surcharge_input:
        return 0.0, surcharge_input
    return 0.0, 0.0


def _calc_discount(discount_input, booking):
    """Return discount as float from input or booking field."""
    if (discount_input or '') == 'Yes':
        return 0.0
    if (discount_input or '').replace('.', '', 1).isdigit():
        return float(discount_input)
    booking_discount = getattr(booking, 'discount', '') or ''
    if booking_discount.replace('.', '', 1).isdigit():
        return float(booking_discount)
    return 0.0


def _get_start_end_points(booking):
    """Derive start/end points from booking fields."""
    if booking.start_point:
        return booking.start_point, booking.end_point
    direction = booking.direction or ""
    addr = f"{booking.street}, {booking.suburb}"
    mapping = [
        ("Drop off to Domestic", addr,                 "Domestic Airport"),
        ("Drop off to Intl",     addr,                 "International Airport"),
        ("Pickup from Domestic", "Domestic Airport",   addr),
        ("Pickup from Intl",     "International Airport", addr),
    ]
    for key, start, end in mapping:
        if key in direction:
            return start, end
    return "Unknown", "Unknown"


def _apply_gst_updates_multi(bookings):
    """Apply 10% GST price update for corporate non-cash bookings (multi-invoice)."""
    for booking in bookings:
        if booking.company_name and not booking.prepay and not booking.cash:
            booking.price = round(float(booking.price) * 1.10, 2)
            booking.prepay = True
            booking.save()


def _build_booking_row(booking, apply_gst_flag, surcharge_input, toll_input):
    """Build a single booking dict row for the multi-invoice table."""
    start_point, end_point = _get_start_end_points(booking)
    price = safe_float(booking.price) or 0.0
    with_gst = round(price * 0.10, 2) if apply_gst_flag else 0.0
    surcharge_calc, surcharge_display = _calc_surcharge(surcharge_input, price)
    toll = safe_float(toll_input) if toll_input else safe_float(booking.toll) or 0.0
    paid = safe_float(booking.paid) or 0.0
    total = price + with_gst + surcharge_calc + toll
    return {
        "pickup_date": booking.pickup_date,
        "pickup_time": booking.pickup_time,
        "start_point": start_point,
        "end_point": end_point,
        "no_of_passenger": booking.no_of_passenger,
        "no_of_baggage": booking.no_of_baggage,
        "message": booking.message,
        "notice": booking.notice,
        "price": price,
        "with_gst": with_gst,
        "surcharge": surcharge_display,
        "toll": toll,
        "total_price": total,
        # private accumulators (stripped before storing in booking_data)
        "_surcharge_calc": surcharge_calc,
        "_paid": paid,
    }


def _build_multi_context(bookings, params, inv_no, today, DEFAULT_BANK):
    """Build (template_name, context) for a multi-booking invoice."""
    _apply_gst_updates_multi(bookings)

    apply_gst_flag = params['apply_gst_flag']
    surcharge_input = params['surcharge_input']
    discount_input = params['discount_input']
    toll_input = params['toll_input']

    booking_data = []
    total_price_without_gst = total_paid = grand_total = 0.0
    total_gst = total_surcharge = total_toll = 0.0

    for booking in bookings:
        row = _build_booking_row(booking, apply_gst_flag, surcharge_input, toll_input)
        total_price_without_gst += row['price']
        total_gst += row['with_gst']
        total_surcharge += row['_surcharge_calc']
        total_toll += row['toll']
        total_paid += row['_paid']
        grand_total += row['total_price']
        booking_data.append({k: v for k, v in row.items() if not k.startswith('_')})

    first_booking = bookings.first() if hasattr(bookings, "first") else (bookings[0] if bookings else None)
    discount = _calc_discount(discount_input, first_booking)
    final_total = grand_total - discount
    total_balance = round(final_total - total_paid, 2)

    context = {
        "inv_no": inv_no,
        "company_name": first_booking.company_name if first_booking else "",
        "name": first_booking.invoice_name if first_booking else "",
        "apply_gst_flag": bool(apply_gst_flag),
        "invoice_date": today,
        "bookings": booking_data,
        "total_price_without_gst": round(total_price_without_gst, 2),
        "with_gst": round(total_gst, 2),
        "surcharge": round(total_surcharge, 2),
        "toll": round(total_toll, 2),
        "discount": discount,
        "total_price": round(final_total, 2),
        "paid": round(total_paid, 2),
        "balance": round(total_balance, 2),
        "DEFAULT_BANK": DEFAULT_BANK,
    }
    return "html_email-multi-invoice.html", context


def _build_single_context(user, users, params, inv_no, today, DEFAULT_BANK):
    """Build (template_name, context) for a single-booking invoice."""
    apply_gst_flag = params['apply_gst_flag']
    surcharge_input = params['surcharge_input']
    discount_input = params['discount_input']
    toll_input = params['toll_input']
    email = params['email']

    start_point = user.start_point
    end_point = user.end_point
    price = safe_float(user.price) or 0.0
    with_gst = round(price * 0.10, 2) if user.company_name else 0.0
    surcharge_calc, surcharge_display = _calc_surcharge(surcharge_input, price)
    toll = safe_float(toll_input) if toll_input else safe_float(user.toll) or 0.0
    discount = _calc_discount(discount_input, user)
    total_price = price + with_gst + surcharge_calc + toll - discount
    float_paid = safe_float(user.paid) or 0.0
    balance = round(total_price - float_paid, 2)

    shared = {
        "inv_no": inv_no,
        "apply_gst_flag": bool(apply_gst_flag),
        "invoice_date": today,
        "toll": toll,
        "discount": discount,
        "DEFAULT_BANK": DEFAULT_BANK,
    }

    if user.cash and user.paid:
        cash_balance = balance - (with_gst + surcharge_calc)
        booker_email = user.booker_email
        context = {
            **shared,
            "name": user.invoice_name, "company_name": user.company_name,
            "contact": user.contact, "email": booker_email or email,
            "pickup_date": user.pickup_date, "pickup_time": user.pickup_time,
            "start_point": start_point, "end_point": end_point,
            "price": user.price, "with_gst": with_gst, "surcharge": surcharge_display,
            "total_price": total_price, "balance": cash_balance, "paid": float_paid,
            "message": user.message, "no_of_passenger": user.no_of_passenger,
            "no_of_baggage": user.no_of_baggage, "notice": user.notice,
            "street": user.street, "suburb": user.suburb,
            "return_pickup_time": user.return_pickup_time,
            "return_pickup_date": user.return_pickup_date,
        }
        return "html_email-invoice-cash.html", context

    if user.return_pickup_time == "x":
        # Round-trip: price is doubled using the second booking record
        user1 = users[1] if len(list(users[:2])) > 1 else None
        base_price = safe_float(user1.price) or 0.0
        base_paid = safe_float(user1.paid) or 0.0
        doubled_price = base_price * 2
        doubled_paid = base_paid * 2
        doubled_with_gst = round(doubled_price * 0.10, 2) if user1.company_name else 0.0
        doubled_surcharge = round(doubled_price * 0.03, 2) if surcharge_input else 0.0
        doubled_total = doubled_price + doubled_with_gst + doubled_surcharge + toll - discount
        balance = round(doubled_total - doubled_paid, 2)
        context = {
            **shared,
            "name": user1.invoice_name, "company_name": user1.company_name,
            "contact": user1.contact,
            "pickup_date": user1.pickup_date, "pickup_time": user1.pickup_time,
            "start_point": user1.start_point, "end_point": user1.end_point,
            "price": doubled_price, "with_gst": doubled_with_gst,
            "surcharge": doubled_surcharge, "total_price": doubled_total,
            "balance": balance, "paid": doubled_paid,
            "message": user1.message, "no_of_passenger": user1.no_of_passenger,
            "no_of_baggage": user1.no_of_baggage, "notice": user1.notice,
            "street": user1.street, "suburb": user1.suburb,
            "return_pickup_time": user1.return_pickup_time,
            "return_pickup_date": user1.return_pickup_date,
        }
        return "html_email-invoice.html", context

    # Standard single booking
    context = {
        **shared,
        "name": user.invoice_name, "company_name": user.company_name,
        "contact": user.contact,
        "pickup_date": user.pickup_date, "pickup_time": user.pickup_time,
        "start_point": start_point, "end_point": end_point,
        "price": user.price, "with_gst": with_gst, "surcharge": surcharge_display,
        "total_price": total_price, "balance": balance, "paid": float_paid,
        "message": user.message, "no_of_passenger": user.no_of_passenger,
        "no_of_baggage": user.no_of_baggage, "notice": user.notice,
        "street": user.street, "suburb": user.suburb,
        "return_pickup_time": user.return_pickup_time,
        "return_pickup_date": user.return_pickup_date,
    }
    return "html_email-invoice.html", context


def _send_invoice_email(template_name, context, recipient_list, inv_no):
    """Render HTML, attach PDF, and dispatch the invoice email."""
    html_content = render_email_template(template_name, context)
    attachments = []
    pdf = render_to_pdf(template_name, context)
    if pdf:
        attachments.append((f"Tax-Invoice-T{inv_no}.pdf", pdf, 'application/pdf'))
    send_html_email(
        f"Tax Invoice #T{inv_no} - EasyGo",
        html_content,
        recipient_list,
        from_email=settings.DEFAULT_FROM_EMAIL,
        attachments=attachments,
    )


# ---------------------------------------------------------------------------
# Main view
# ---------------------------------------------------------------------------

@require_turnstile
def invoice_detail(request):
    if request.method != "POST":
        return render(request, 'basecamp/invoice.html', {})

    params = _parse_invoice_params(request)
    email = params['email']

    try:
        index = parse_one_based_index(params['index'])
    except ValueError:
        return HttpResponse("Invalid index value", status=400)

    # booker_email로 먼저 검색, 없으면 email로 검색
    users = Post.objects.filter(booker_email__iexact=email)
    if not users.exists():
        users = Post.objects.filter(email__iexact=email)

    if not users.exists():
        return HttpResponse("No bookings found", status=404)

    user = users[0]
    today = date.today()
    inv_no = _resolve_inv_no(user, params['inv_no'])
    DEFAULT_BANK = getattr(settings, "DEFAULT_BANK_CODE", "westpac")

    bookings, multiple = _resolve_bookings(users, index, params['from_date'], params['to_date'])
    if multiple and not bookings.exists():
        return HttpResponse("No bookings found in selected date range", status=404)

    if multiple:
        template_name, context = _build_multi_context(bookings, params, inv_no, today, DEFAULT_BANK)
    else:
        user = bookings[0]
        if not user:
            return HttpResponse("No booking found", status=404)
        template_name, context = _build_single_context(user, users, params, inv_no, today, DEFAULT_BANK)

    first_user = users[0]
    customer_recipients = [first_user.booker_email] if first_user.booker_email else list(filter(None, [first_user.email, first_user.email1]))
    _send_invoice_email(template_name, context, customer_recipients + [RECIPIENT_EMAIL], inv_no)

    if not multiple and user.company_name and not user.prepay and not user.cash:
        user.price = round(float(user.price) * 1.10, 2)
        user.prepay = True
        user.save()

    return render_inquiry_done(request)
    

# --------------------------
# PayPal IPN Handler
# --------------------------
PAYPAL_VERIFY_URL = "https://ipnpb.paypal.com/cgi-bin/webscr"

@csrf_exempt
@require_POST
def paypal_ipn(request):
    if request.method == 'POST':        
        item_name = request.POST.get('item_name')
        payer_email = request.POST.get('payer_email')
        gross_amount = request.POST.get('mc_gross')
        txn_id = request.POST.get('txn_id')

        if PaypalPayment.objects.filter(txn_id=txn_id).exists():
            return HttpResponse(status=200, content="Duplicate IPN Notification")
        
        p = PaypalPayment(name=item_name, email=payer_email, amount=gross_amount, txn_id=txn_id)

        try:
            p.save()

        except Exception as e:
            paypal_ipn_error_email('PayPal IPN Error', str(e), item_name, payer_email, gross_amount)
            return HttpResponse(status=500, content="Error processing PayPal IPN")

        ipn_data = request.POST.copy()
        ipn_data['cmd'] = '_notify-validate'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(PAYPAL_VERIFY_URL, data=ipn_data, headers=headers, verify=True)
            response_content = response.text.strip()
            
            if response.status_code == 200 and response_content == 'VERIFIED':
                return HttpResponse(status=200)
            else:
                paypal_ipn_error_email('PayPal IPN Verification Failed', 'Failed to verify PayPal IPN.', item_name, payer_email, gross_amount)
                return HttpResponse(status=500, content="Error processing PayPal IPN")

        except requests.exceptions.RequestException as e:
            paypal_ipn_error_email('PayPal IPN Request Exception', str(e), item_name, payer_email, gross_amount)
            return HttpResponse(status=500, content="Error processing PayPal IPN")

    return HttpResponse(status=400)


# --------------------------
# Stripe Checkout Session
# --------------------------

@ratelimit(key='ip', rate='5/m', method='POST', block=False)
@csrf_exempt
@require_POST
def create_stripe_checkout_session(request):
    if request.method == 'POST':
        if getattr(request, 'limited', False):
            if is_ajax(request):
                return JsonResponse({'success': False, 'message': 'Too many requests. Please wait a moment and try again.'}, status=429)
            return render(request, 'basecamp/403.html', status=429)
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
            'price': 'price_1PRwKAI9LkpP3oK9hQF7BHj7', 
            'quantity': 1,
            }],
            mode='payment',
            success_url='https://easygoshuttle.com.au/success/',
            cancel_url='https://easygoshuttle.com.au/cancel/',                
        )
        
        return JsonResponse({'id': session.id})
       

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    if not sig_header:
        return HttpResponse(status=400)
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        print('Error parsing payload: {}'.format(str(e)))
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print('Error verifying webhook signature: {}'.format(str(e)))
        return HttpResponse(status=400)

    if event.type == 'checkout.session.completed':
        session = event.data.object
        print('PaymentIntent was successful!')
        handle_checkout_session_completed(session)

    else:
        print(f'Unhandled event type: {event.type}')

    return HttpResponse(status=200)