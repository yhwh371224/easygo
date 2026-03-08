from datetime import datetime, date
import requests
import stripe
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from utils.email import send_html_email
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from main.settings import RECIPIENT_EMAIL, DEFAULT_FROM_EMAIL
from blog.models import Post, PaypalPayment
from csp.constants import NONCE
from basecamp.basecamp_utils import (
    render_to_pdf, safe_float,
    handle_checkout_session_completed, paypal_ipn_error_email,
    verify_turnstile, render_email_template,
    render_inquiry_done, require_turnstile, parse_one_based_index,
)


@require_turnstile
def invoice_detail(request):
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        extra_email = request.POST.get('extra_email', '').strip()
        apply_gst_flag = request.POST.get('apply_gst')
        surcharge_input = request.POST.get('surcharge')
        discount_input = request.POST.get('discount')
        inv_no = request.POST.get('inv_no')
        toll_input = request.POST.get('toll')
        index = request.POST.get('index', '1')
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')

        try:
            index = parse_one_based_index(index)
        except ValueError:
            return HttpResponse("Invalid index value", status=400)

        users = Post.objects.filter(email__iexact=email)
        if not users.exists():
            return HttpResponse("No bookings found", status=404)
        else:
            user = users[0]
            today = date.today()
            # ✅ Use provided inv_no if exists, else use old logic
            if inv_no and inv_no.strip():
                inv_no = inv_no.strip()
            else:
                inv_no = f"{user.pickup_date.toordinal()}" if user.pickup_date else "896021"

        DEFAULT_BANK = getattr(settings, "DEFAULT_BANK_CODE", "westpac")

        # Multi booking 여부
        multiple = False
        if from_date and to_date:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            bookings = users.filter(pickup_date__range=(from_date_obj, to_date_obj)).order_by('pickup_date', 'pickup_time')
            multiple = True
            if not bookings.exists():
                return HttpResponse(
                    "No bookings found in selected date range",
                    status=404
                )
        else:
            bookings = [users[index]] if 0 <= index < len(users) else [users.first()]

        if multiple:
            for booking in bookings:
                if booking.company_name and not booking.prepay:
                    if not user.cash:  # 🚨 cash인 경우는 제외
                        booking.price = round(float(booking.price) * 1.10, 2)
                        booking.prepay = True
                        booking.save()

            booking_data = []
            total_price_without_gst = total_paid = grand_total = 0
            total_gst = total_surcharge = total_toll = 0

            for booking in bookings:
                if booking.start_point:
                    start_point = booking.start_point
                    end_point = booking.end_point
                    # 리턴 구간 존재 시 덮어쓰기 또는 별도 처리
                    if getattr(booking, 'return_start_point', None):
                        return_start_point = booking.return_start_point
                        return_end_point = booking.return_end_point
                    else:
                        return_start_point = None
                        return_end_point = None
                else:
                    direction = booking.direction or ""
                    if "Drop off to Domestic" in direction:
                        start_point = f"{booking.street}, {booking.suburb}"
                        end_point = "Domestic Airport"
                    elif "Drop off to Intl" in direction:
                        start_point = f"{booking.street}, {booking.suburb}"
                        end_point = "International Airport"
                    elif "Pickup from Domestic" in direction:
                        start_point = "Domestic Airport"
                        end_point = f"{booking.street}, {booking.suburb}"
                    elif "Pickup from Intl" in direction:
                        start_point = "International Airport"
                        end_point = f"{booking.street}, {booking.suburb}"
                    else:
                        start_point = "Unknown"
                        end_point = "Unknown"

                price = safe_float(booking.price) or 0.0
                with_gst = round(price * 0.10, 2) if apply_gst_flag else 0.0

                # ✅ Surcharge handling
                if surcharge_input == "Yes":
                    surcharge_calc = round(price * 0.03, 2)
                    surcharge_display = surcharge_calc
                elif surcharge_input:
                    surcharge_calc = 0.0
                    surcharge_display = surcharge_input
                else:
                    surcharge_calc = 0.0
                    surcharge_display = 0.0

                toll = safe_float(toll_input) if toll_input else safe_float(booking.toll) or 0.0
                paid = safe_float(booking.paid) or 0.0
                total = price + with_gst + surcharge_calc + toll

                total_price_without_gst += price
                total_gst += with_gst
                total_surcharge += surcharge_calc
                total_toll += toll
                total_paid += paid
                grand_total += total

                paid = safe_float(booking.paid) or 0.0

                booking_data.append({
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
                })

            first_booking = bookings.first() if hasattr(bookings, "first") else (bookings[0] if bookings else None)

            if (discount_input or '') == 'Yes':
                discount = 0.0
            elif (discount_input or '').replace('.', '', 1).isdigit():
                discount = float(discount_input)
            elif first_booking and (first_booking.discount or '').replace('.', '', 1).isdigit():
                discount = float(first_booking.discount)
            else:
                discount = 0.0

            final_total = grand_total - discount
            total_balance = round(final_total - total_paid, 2)

            DEFAULT_BANK = getattr(settings, "DEFAULT_BANK_CODE", "westpac")

            first_booking = bookings[0] if bookings else None

            context = {
                "inv_no": inv_no,
                "company_name": first_booking.company_name if first_booking else "",
                "name": first_booking.name if first_booking else "",
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

            template_name = "html_email-multi-invoice.html"
            html_content = render_email_template(template_name, context)

        else:
            user = bookings[0]
            if not user:
                return HttpResponse("No booking found", status=404)

            start_point = user.start_point
            end_point = user.end_point

            price = safe_float(user.price) or 0.0
            with_gst = round(price * 0.10, 2) if user.company_name else 0.0

            # Surcharge handling
            if surcharge_input == "Yes":
                surcharge_calc = round(price * 0.03, 2)
                surcharge_display = surcharge_calc
            elif surcharge_input:
                surcharge_calc = 0.0
                surcharge_display = surcharge_input
            else:
                surcharge_calc = 0.0
                surcharge_display = 0.0

            toll = safe_float(toll_input) if toll_input else safe_float(user.toll) or 0.0

            if (discount_input or '') == 'Yes':
                discount = 0.0
            elif (discount_input or '').replace('.', '', 1).isdigit():
                discount = float(discount_input)
            elif (user.discount or '').replace('.', '', 1).isdigit():
                discount = float(user.discount)
            else:
                discount = 0.0

            total_price = price + with_gst + surcharge_calc + toll - discount
            float_paid = safe_float(user.paid) or 0.0
            balance = round(total_price - float_paid, 2)

            if user.cash and user.paid:
                cash_balance = balance - (with_gst + surcharge_calc)
                template_name = "html_email-invoice-cash.html"
                context = {
                    "inv_no": inv_no, "name": user.name, "company_name": user.company_name,
                    "apply_gst_flag": bool(apply_gst_flag),
                    "contact": user.contact, "discount": discount, "email": email,
                    "pickup_date": user.pickup_date, "pickup_time": user.pickup_time,    
                    "start_point": start_point, "end_point": end_point, "invoice_date": today,
                    "price": user.price, "with_gst": with_gst, "surcharge": surcharge_display,
                    "total_price": total_price, "toll": toll, "balance": cash_balance, 
                    "paid": float_paid, "message": user.message, "no_of_passenger": user.no_of_passenger,
                    "no_of_baggage": user.no_of_baggage, "notice": user.notice, "street": user.street, "suburb": user.suburb,
                    "return_pickup_time": user.return_pickup_time, "return_pickup_date": user.return_pickup_date, "DEFAULT_BANK": DEFAULT_BANK, 
                }

            elif user.return_pickup_time == "x":
                user1 = users[1] if len(list(users[:2])) > 1 else None

                # 두 배 가격 계산
                base_price = safe_float(user1.price) or 0.0
                base_paid = safe_float(user1.paid) or 0.0

                doubled_price = base_price * 2
                doubled_paid = base_paid * 2  
                doubled_with_gst = round(doubled_price * 0.10, 2) if user1.company_name else 0.0
                doubled_surcharge = round(doubled_price * 0.03, 2) if surcharge_input else 0.0
                doubled_total = doubled_price + doubled_with_gst + doubled_surcharge + toll - discount
                balance = round(doubled_total - doubled_paid, 2)

                template_name = "html_email-invoice.html"
                context = {
                    "inv_no": inv_no, "name": user1.name, "company_name": user1.company_name,
                    "apply_gst_flag": bool(apply_gst_flag),
                    "contact": user1.contact, "pickup_date": user1.pickup_date, "pickup_time": user1.pickup_time,   
                    "start_point": user1.start_point, "end_point": user1.end_point, "invoice_date": today,
                    "price": doubled_price, "with_gst": doubled_with_gst, "surcharge": doubled_surcharge,
                    "total_price": doubled_total, "toll": toll, "balance": balance, "discount": discount,
                    "paid": doubled_paid, "message": user1.message, "no_of_passenger": user1.no_of_passenger,
                    "no_of_baggage": user1.no_of_baggage, "notice": user1.notice, "street": user1.street, "suburb": user1.suburb,
                    "return_pickup_time": user1.return_pickup_time, "return_pickup_date": user1.return_pickup_date, "DEFAULT_BANK": DEFAULT_BANK, 
                }
            else:
                template_name = "html_email-invoice.html"
                context = {
                    "inv_no": inv_no, "name": user.name, "company_name": user.company_name,
                    "apply_gst_flag": bool(apply_gst_flag),
                    "contact": user.contact, "pickup_date": user.pickup_date, "pickup_time": user.pickup_time,  
                    "start_point": start_point, "end_point": end_point, "invoice_date": today,
                    "price": user.price, "with_gst": with_gst, "surcharge": surcharge_display,
                    "total_price": total_price, "toll": toll, "balance": balance, "discount": discount,
                    "paid": float_paid, "message": user.message, "no_of_passenger": user.no_of_passenger,
                    "no_of_baggage": user.no_of_baggage, "notice": user.notice, "street": user.street, "suburb": user.suburb,
                    "return_pickup_time": user.return_pickup_time, "return_pickup_date": user.return_pickup_date, "DEFAULT_BANK": DEFAULT_BANK, 
                }

            html_content = render_email_template(template_name, context)

        recipient_list = [email, RECIPIENT_EMAIL]
        if extra_email:
            recipient_list.append(extra_email)

        attachments = []
        pdf = render_to_pdf(template_name, context)
        if pdf:
            attachments.append((f"Tax-Invoice-T{inv_no}.pdf", pdf, 'application/pdf'))

        send_html_email(
            f"Tax Invoice #T{inv_no} - EasyGo",
            html_content,
            recipient_list,
            from_email=DEFAULT_FROM_EMAIL,
            attachments=attachments,
        )

        if not multiple and user.company_name and not user.prepay:
            if not user.cash:  
                user.price = round(float(user.price) * 1.10, 2)
                user.prepay = True
                user.save()

        return render_inquiry_done(request)

    else:
        return render(request, 'basecamp/invoice.html', {})
    

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

@csrf_exempt
@require_POST
def create_stripe_checkout_session(request):
    if request.method == 'POST':
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
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
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