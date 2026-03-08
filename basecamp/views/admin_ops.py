from datetime import datetime, date, timedelta
import logging
import stripe
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from utils.email import send_text_email, send_template_email
from main.settings import RECIPIENT_EMAIL
from blog.models import Post, Inquiry, Driver
from blog.sms_utils import send_sms_notice, send_whatsapp_template
from csp.constants import NONCE
from basecamp.basecamp_utils import (
    parse_baggage, parse_date, handle_email_sending, format_pickup_time_12h,
    to_bool,
    render_inquiry_done, parse_booking_dates, get_customer_status,
    parse_one_based_index, resolve_payment_flags,
)


logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_LIVE_SECRET_KEY


# Booking by myself 
def confirmation_detail(request):
    if request.method == "POST":
        pickup_date_str = request.POST.get('pickup_date', '')           
        return_pickup_date_str = request.POST.get('return_pickup_date', '')
        company_name = request.POST.get('company_name', '')
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        email1 = request.POST.get('email1', '')   
        flight_number = request.POST.get('flight_number', '')
        flight_time = request.POST.get('flight_time', '')
        pickup_time = request.POST.get('pickup_time')
        direction = request.POST.get('direction', '')
        suburb = request.POST.get('suburb', '')
        street = request.POST.get('street', '')
        start_point = request.POST.get('start_point', '')
        end_point = request.POST.get('end_point', '')
        no_of_passenger = request.POST.get('no_of_passenger')
        return_direction = request.POST.get('return_direction')
        return_flight_number = request.POST.get('return_flight_number', '')
        return_flight_time = request.POST.get('return_flight_time', '')
        return_pickup_time = request.POST.get('return_pickup_time')
        return_start_point = request.POST.get('return_start_point', '')
        return_end_point = request.POST.get('return_end_point', '')
        message = request.POST.get('message', '') 
        notice = request.POST.get('notice', '')       
        price = request.POST.get('price', '')
        paid = request.POST.get('paid', '')
        cash = to_bool(request.POST.get('cash', ''))
        prepay = to_bool(request.POST.get('prepay', ''))  

        try:
            pickup_date_obj, return_pickup_date_obj = parse_booking_dates(pickup_date_str, return_pickup_date_str)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        data = {            
            'name': name,
            'contact': contact,
            'email': email,
            'pickup_date': pickup_date_obj.strftime('%Y-%m-%d'),
            'flight_number': flight_number,
            'pickup_time': pickup_time,
            'start_point': start_point,
            'street': street,
            'end_point': end_point,
            'no_of_passenger': no_of_passenger,
            'message': message,
        }    
        
        status_message, subject = get_customer_status(email, name, subject_prefix="[Confirmation] ")
        data['status_message'] = status_message

        email_content_template = '''
        Hello, {name} \n
        {status_message}\n
        *** It starts from Home Page
        =============================
        Contact: {contact}
        Email: {email}
        ✅ Pickup date: {pickup_date}
        Flight number: {flight_number}
        Pickup time: {pickup_time}
        start_point: {start_point}
        Street: {street}
        end_point: {end_point}
        Passenger: {no_of_passenger}
        Message: {message}
        =============================\n
        Best Regards,
        EasyGo Admin \n\n
        '''

        content = email_content_template.format(**data)

        send_text_email(subject, content, [RECIPIENT_EMAIL])

        sam_driver = Driver.objects.get(driver_name="Sam") 

        # 🧳 개별 수하물 항목 수집
        baggage_str = parse_baggage(request)

        p = Post(company_name=company_name, name=name, contact=contact, email=email, email1=email1, pickup_date=pickup_date_obj, flight_number=flight_number,
                 flight_time=flight_time, pickup_time=pickup_time, start_point=start_point, end_point=end_point, direction=direction, suburb=suburb, street=street,
                 no_of_passenger=no_of_passenger, no_of_baggage=baggage_str, message=message, return_direction=return_direction, return_pickup_date=return_pickup_date_obj, 
                 return_flight_number=return_flight_number, return_flight_time=return_flight_time, return_pickup_time=return_pickup_time, return_start_point=return_start_point,
                 return_end_point=return_end_point, notice=notice, price=price, paid=paid, cash=cash, prepay=prepay, driver=sam_driver)
        
        p.save()        

        return JsonResponse({'success': True, 'redirect_url': '/inquiry_done/'})

    else:
        return render(request, 'basecamp/booking/confirmation.html', {})

# sending confirmation email first one   
def sending_email_first_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        prepay_raw = request.POST.get('prepay')  # May be None
        cash_raw = request.POST.get('cash')  # May be None
        index = request.POST.get('index', '1')
        try:
            index = parse_one_based_index(index)
        except ValueError:
            return HttpResponse("Invalid index value", status=400)

        users = Post.objects.filter(email__iexact=email)
        if users.exists() and 0 <= index < len(users):
            user = users[index]  

            # price 처리
            if user.price in [None, ""]:
                display_price = "TBA"
            else:
                display_price = user.price

            final_prepay, final_cash = resolve_payment_flags(prepay_raw, cash_raw, user)

            user.prepay = final_prepay
            user.cash = final_cash
            user.price = display_price
            user.sent_email = True
            user.save()
            
            if user.cancelled: 
                template_name = "html_email-cancelled.html"
                subject = "Booking Cancellation Notice - EasyGo" 
                
                context = {
                    'name': user.name, 
                    'email': user.email,
                    'pickup_date': user.pickup_date or "",
                    'pickup_time': user.pickup_time or "",
                    'return_pickup_date': user.return_pickup_date or "",
                    'return_pickup_time': user.return_pickup_time or "", 
                        }

                handle_email_sending(request, user.email, subject, template_name, context)
                    
            else: 
                template_name = "html_email-confirmation.html"

                send_template_email(
                    "Booking confirmation - EasyGo",
                    "html_email-confirmation.html",
                    {
                        'company_name': user.company_name, 'name': user.name, 'contact': user.contact, 'email': user.email, 'email1': user.email1,
                        'pickup_date': user.pickup_date, 'flight_number': user.flight_number,
                        'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                        'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                        'no_of_passenger': user.no_of_passenger, 'no_of_baggage': user.no_of_baggage,
                        'return_direction': user.return_direction, 'return_pickup_date': user.return_pickup_date,
                        'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time,
                        'return_pickup_time': user.return_pickup_time, 'message': user.message, 'notice': user.notice,
                        'price': display_price, 'paid': user.paid, 'cash': final_cash, 'prepay': final_prepay,
                        'toll': getattr(user, 'toll', 0), 'start_point': getattr(user, 'start_point', ''),
                        'end_point': getattr(user, 'end_point', ''), 'return_start_point': getattr(user, 'return_start_point', ''),
                        'return_end_point': getattr(user, 'return_end_point', ''),
                    },
                    [email, RECIPIENT_EMAIL],
                    request=request,
                )

            return render_inquiry_done(request)

        else:
            return HttpResponse("No user found", status=400)

    else:
        return render(request, 'basecamp/email/sending_email_first.html', {})
    

# sending confirmation email second one    
def sending_email_second_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')
        prepay_raw = request.POST.get('prepay')  # May be None
        cash_raw = request.POST.get('cash')  # May be None

        users = list(Post.objects.filter(email__iexact=email)[:2])
        user1 = users[0] if len(users) > 0 else None
        user  = users[1] if len(users) > 1 else None

        # prepay / cash 처리
        final_prepay, final_cash = resolve_payment_flags(prepay_raw, cash_raw, user, user1)

        user.prepay = final_prepay
        user.cash = final_cash
        user.sent_email = True

        user1.prepay = final_prepay
        user1.cash = final_cash
        user1.sent_email = True

        # price 안전 처리 및 DB에 저장
        if user.price in [None, ""]:
            user.price = "TBA"
        if user1.price in [None, ""]:
            user1.price = "TBA"

        user.save()
        user1.save()

        # price 계산 (숫자가 아니면 0으로 처리)
        price1 = float(user.price) if isinstance(user.price, (int, float, str)) and str(user.price).replace('.', '', 1).isdigit() else 0
        price2 = float(user1.price) if isinstance(user1.price, (int, float, str)) and str(user1.price).replace('.', '', 1).isdigit() else 0
        double_price = price1 + price2

        # paid 계산
        paid1 = float(user.paid) if user.paid else 0
        paid2 = float(user1.paid) if user1.paid else 0
        double_paid = paid1 + paid2

        if user.cancelled or user1.cancelled:
            template_name = "html_email-cancelled.html"
            subject = "Booking Cancellation Notice - EasyGo" 
            
            context = {
                'name': user.name, 
                'email': user.email,
                'pickup_date': user.pickup_date or "",
                'pickup_time': user.pickup_time or "",
                'return_pickup_date': user.return_pickup_date or "",
                'return_pickup_time': user.return_pickup_time or "", 
            }

            handle_email_sending(request, user.email, subject, template_name, context)

        else:
            template_name = "html_email-confirmation.html"
            subject = "Booking confirmation - EasyGo"

            context = { 
                'company_name': user.company_name, 
                'name': user.name, 
                'contact': user.contact, 
                'email': user.email, 
                'email1': user.email1,
                'pickup_date': user.pickup_date, 
                'flight_number': user.flight_number,
                'flight_time': user.flight_time, 
                'pickup_time': user.pickup_time,
                'direction': user.direction, 
                'street': user.street, 
                'suburb': user.suburb, 
                'start_point': getattr(user, 'start_point', ''),
                'no_of_passenger': user.no_of_passenger, 
                'no_of_baggage': user.no_of_baggage, 
                'end_point': getattr(user, 'end_point', ''),
                'return_direction': user.return_direction, 
                'return_pickup_date': user.return_pickup_date, 
                'return_flight_number': user.return_flight_number, 
                'return_flight_time': user.return_flight_time, 
                'return_pickup_time': user.return_pickup_time, 
                'message': user.message, 
                'notice': user.notice, 
                'price': f"{user.price} + {user1.price}" if "TBA" in [user.price, user1.price] else double_price,
                'paid': double_paid, 
                'cash': user.cash, 
                'prepay': user.prepay,
                'toll': getattr(user, 'toll', 0), 
                'return_start_point': getattr(user, 'return_start_point', ''), 
                'return_end_point': getattr(user, 'return_end_point', ''), 
            }

            recipient_list = [user.email, RECIPIENT_EMAIL]
            if user.email1:
                recipient_list.append(user.email1)

            send_template_email(subject, template_name, context, recipient_list, request=request)
            
        return render_inquiry_done(request)

    else:
        return render(request, 'basecamp/email/sending_email_second.html', {})
    

def sending_email_input_data_detail(request):     
    if request.method == "POST":
        email = request.POST.get('email')   
        field = request.POST.get('field')        

        inquiry = Inquiry.objects.filter(email__iexact=email).first()
        post = Post.objects.filter(email__iexact=email).first()

        user = None
        for obj in [inquiry, post]:
            if obj:
                if user is None or obj.created > user.created:
                    user = obj

        if not user:
            return render(request, 'basecamp/400.html')

        else:
            template_name = "html_email-input-date.html"
            subject = "Checking details - EasyGo"

            # 템플릿에 전달할 컨텍스트 구성
            context = {
                'name': user.name, 'contact': user.contact, 'email': user.email, 
                'pickup_date': user.pickup_date, 'flight_number': user.flight_number,
                'flight_time': user.flight_time, 'pickup_time': user.pickup_time,
                'direction': user.direction, 'street': user.street, 'suburb': user.suburb,
                'no_of_baggage': user.no_of_baggage, 'field': field, 
                'start_point': user.start_point, 'end_point': user.end_point,
                'return_start_point': user.return_start_point, 'return_end_point': user.return_end_point,
                'return_direction': user.return_direction, 'return_pickup_date': user.return_pickup_date, 
                'return_flight_number': user.return_flight_number, 'return_flight_time': user.return_flight_time, 
                'return_pickup_time': user.return_pickup_time,'message': user.message, 'notice': user.notice, 
            }

            handle_email_sending(request, user.email, subject, template_name, context)

        return render_inquiry_done(request)

    else:
        return render(request, 'basecamp/email/sending_email_first.html', {})


# email dispatching
def email_dispatch_detail(request):
    if request.method == "POST":
        honeypot = request.POST.get('phone_verify', '')
        if honeypot != '':
            return JsonResponse({'success': False, 'error': 'Bot detected.'})
        # 1️⃣ Form fields
        email = request.POST.get('email', '').strip()
        selected_option = request.POST.get('selected_option')
        adjusted_pickup_time = request.POST.get('adjusted_pickup_time')
        payment_method = request.POST.get("payment_method")
        payment_amount = request.POST.get('payment_amount')
        remain_first_booking = 'remain_first_booking' in request.POST
        remain_return_booking = 'remain_return_booking' in request.POST
        wait_duration = request.POST.get('wait_duration')
        discount_price = request.POST.get('discount_price')

        # 2️⃣ User 찾기
        user = (
            Post.objects.select_related('driver').filter(
                Q(email__iexact=email) | Q(email1__iexact=email)
            ).first()
            or Inquiry.objects.filter(email__iexact=email).first()
        )

        if not user:
            logger.warning(f"User not found for email: {email}")

        pickup_time_12h = None

        # 3️⃣ Adjusted pickup time 처리
        if adjusted_pickup_time and user:
            users = Post.objects.filter(email=email, pickup_date__gte=date.today()).order_by('pickup_date')
            if users.exists():
                closest_user = users.first()
                closest_user.pickup_time = adjusted_pickup_time
                closest_user.save()

                message = "Important Notice! Please check your email and respond only via email - EasyGo Airport Shuttle"
                if closest_user.contact:
                    send_sms_notice(closest_user.contact, message)

                pickup_time_12h = format_pickup_time_12h(adjusted_pickup_time)

        # 4️⃣ Email template mapping
        template_options = {
            "Gratitude For Payment": ("html_email-response-payment-received.html", "Payment Received - EasyGo"),
            "Pickup Notice for Today": ("html_email-today1.html", "Important Update for Today's Pickup - EasyGo "),
            "Payment Method": ("html_email-response-payment.html", "Payment Method - EasyGo"),
            "PayPal Assistance": ("html_email-response-payment-assistance.html", "PayPal Assistance - EasyGo"),
            "Inquiry for driver contact": ("html_email-response-driver-contact.html", "Inquiry for driver contact - EasyGo"),
            "Airport Pickup Guide": ("html_email-response-arrival-guide.html", "Airport Pickup Guide - EasyGo"),
            'Earlier Pickup Requested for Departure': ("html_email-departure-early.html", "Urgent notice - EasyGo"),
            'Later Pickup Requested for Departure': ("html_email-departure-late.html", "Urgent notice - EasyGo"),
            'Early Arrival Notification': ("html_email-arrival-early.html", "Urgent notice - EasyGo"),
            'Arrival Later Than Scheduled': ("html_email-arrival-late.html", "Urgent notice - EasyGo"),
            'Notice of Delay': ("html_email-just-late-notice.html", "Urgent notice - EasyGo"),
            'Adjusted Pickup Time': ("html_email-just-adjustment.html", "Urgent notice - EasyGo"),
            "Meeting Point Inquiry": ("html_email-response-meeting.html", "Meeting Point - EasyGo"),
            "Payment in Advance Required": ("html_email-response-prepayment.html", "Payment in Advance Required - EasyGo"),
            "Further details for booking": ("html_email-response-more-details.html", "Further details for booking - EasyGo"),
            "Further details for booked": ("html_email-response-details-booked.html", "Further details for booked - EasyGo"),
            "Arrival Pickup Arrangement Without Payment": ("html_email-urgent-arrival-pickup.html", "Arrival Pickup Arrangement Without Payment - EasyGo"),
            "Shared Ride (inquiry) Discount Offer": ("html_email-shared-inquiry-discount.html", "Discount notice - EasyGo"),
            "Shared Ride (booking) Discount Offer": ("html_email-shared-booking-discount.html", "Discount notice - EasyGo"),
            "Cancellation of Booking": ("html_email-response-cancel.html", "Cancellation of Booking: EasyGo"),
            "Apologies Cancellation of Booking": ("html_email-response-cancel1.html", "Apologies Cancellation of Booking: EasyGo"),
            "Cancellation by Client": ("html_email-response-cancelby.html", "Confirmed Booking Cancellation: EasyGo"),
            "Apology for oversight": ("html_email-apology-for-oversight.html", "Apology for oversight: EasyGo"),
            "Payment discrepancy": ("html_email-response-discrepancy.html", "Payment discrepancy: EasyGo"),
            "Special promotion": ("html_email-special-promotion.html", "Special promotion: EasyGo"),
            "Booking delay": ("html_email-booking-delay.html", "Booking delay: EasyGo"),
            "Booking delay 1": ("html_email-booking-delay1.html", "Booking delay 1: EasyGo")
        }

        if selected_option in template_options:
            template_name, subject = template_options[selected_option]

        # 5️⃣ Template 적용
        context = {
            'email': email,
            'name': user.name if user else '',
            'adjusted_pickup_time': adjusted_pickup_time,
            'payment_amount': payment_amount,
            'remain_first_booking': remain_first_booking,    
            'remain_return_booking': remain_return_booking,
            'wait_duration': wait_duration,
            'discount_price': discount_price
        }

        if pickup_time_12h:
            context['pickup_time_12h'] = pickup_time_12h

        # driver info
        if hasattr(user, 'driver') and user.driver:
            context.update({
                'driver': user.driver,
                'driver_name': user.driver.driver_name,
                'driver_contact': user.driver.driver_contact,
                'driver_plate': user.driver.driver_plate,
                'driver_car': user.driver.driver_car,
            })

        # 옵션별 특수 처리
        # ✅ Pickup Notice Today
        if selected_option == "Pickup Notice for Today":
            today = date.today()
            user_today = Post.objects.filter(email=email, pickup_date=today).first()
            if user_today:
                context.update({
                    'pickup_time': user_today.pickup_time,
                    'contact': user_today.contact,
                    'meeting_point': user_today.meeting_point,
                    'direction': user_today.direction,
                    'cash': user_today.cash,
                    'cruise': user_today.cruise,
                    'sms_reminder': user_today.sms_reminder 
                })

        # ✅ Gratitude For Payment
        if selected_option == "Gratitude For Payment":
            try:
                payment_amount = float(payment_amount)
                if payment_amount <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                return JsonResponse({
                    'success': False,
                    'error': "Payment amount must be a number greater than 0."
                }, status=400)

            remaining_amount = payment_amount

            bookings = (
                Post.objects
                .filter(email__iexact=email, pickup_date__gte=date.today())
                .order_by('pickup_date')
            )

            applied_bookings = []

            for booking in bookings:
                price = float(booking.price)
                paid = float(booking.paid or 0)

                # 이미 전액 결제 → 완전히 스킵
                if paid >= price:
                    continue

                due = price - paid
                apply_amount = min(remaining_amount, due)

                # 적용할 금액이 없으면 스킵
                if apply_amount <= 0:
                    continue

                # ✅ 여기부터가 "돈이 실제로 적용된 예약"만
                booking.paid = paid + apply_amount

                original_notice = (booking.notice or "").strip()
                paid_text = f"===Gratitude=== Applied: ${apply_amount}"
                if "===Gratitude===" not in original_notice:
                    booking.notice = (
                        f"{original_notice} | {paid_text}"
                        if original_notice else paid_text
                    )

                booking.reminder = True
                booking.toll = ""
                booking.cash = False
                booking.pending = False

                applied_bookings.append(booking)

                remaining_amount -= apply_amount

                if remaining_amount <= 0:
                    break

            if applied_bookings:
                Post.objects.bulk_update(
                    applied_bookings,
                    ['paid', 'notice', 'reminder', 'toll', 'cash', 'pending'],
                    batch_size=50,
                )

            context.update({
                'applied_bookings': applied_bookings,
                'payment_amount': payment_amount,
            })

        # ✅ Cancellation
        if selected_option in ["Cancellation of Booking", "Cancellation by Client", "Apologies Cancellation of Booking"]:

            user1 = None
            if user.return_pickup_time == 'x':
                try:
                    user1 = Post.objects.filter(email__iexact=user.email)[1]
                except IndexError:
                    user1 = None

            # 취소 처리
            if user.return_pickup_time == 'x':  # 왕복 예약
                # ① 첫 번째 ❌ / 두 번째 ❌ (모두 취소)
                if not remain_first_booking and not remain_return_booking:
                    user.cancelled = True
                    user.pending = False
                    user.save()

                    if user1:
                        user1.cancelled = True
                        user1.pending = False
                        user1.save()

                # ② 첫 번째 ✅ / 두 번째 ❌
                elif remain_first_booking and not remain_return_booking:
                    user.cancelled = True
                    user.pending = False
                    user.save()

                # ③ 첫 번째 ❌ / 두 번째 ✅
                elif not remain_first_booking and remain_return_booking:
                    if user1:
                        user1.cancelled = True
                        user1.pending = False
                        user1.save()

            else:  # 단일 예약
                user.cancelled = True
                user.pending = False
                user.save()

            # context 업데이트 (한 번만)
            context.update({
                'booking_date': user.pickup_date,
                'return_booking_date': user1.pickup_date if user1 else None,
                'remain_first_booking': remain_first_booking,
                'remain_return_booking': remain_return_booking,
            })

            # Apology SMS
            if selected_option == "Apologies Cancellation of Booking" and user.contact:
                message = (
                    f"EasyGo - Urgent notice!\n\n"
                    f"Dear {user.name}, We have sent an urgent email. Please check your email.\n"
                    "Reply only via email >> info@easygoshuttle.com.au"
                )
                send_sms_notice(user.contact, message)
                send_whatsapp_template(user.contact, user.name)

            # Apology SMS
            if selected_option == "Apologies Cancellation of Booking" and user.contact:
                message = f"EasyGo - Urgent notice!\n\nDear {user.name}, We have sent an urgent email. Please check your email.\nReply only via email >> info@easygoshuttle.com.au"
                send_sms_notice(user.contact, message)
                send_whatsapp_template(user.contact, user.name)


        # ✅ Payment discrepancy
        if selected_option == "Payment discrepancy" and user:
            diff = round(float(user.price) - float(user.paid), 2)
            if diff > 0:
                user.toll = "short payment"
                context.update({'price': user.price, 'paid': user.paid, 'diff': f"{diff:.2f}"})
                user.save()

        # ✅ Payment Confirmed
        if selected_option == "Payment Confirmed":
            if payment_method == "cash":
                user.cash = True
                user.prepay = False
                user.pending = False
                template_name = "html_email-response-cash-payment-confirmed.html"
                subject = "Cash Payment Confirmed - EasyGo"
            elif payment_method == "card":
                user.cash = False
                user.pending = True
                user.prepay = True
                template_name = "html_email-response-card-payment-confirmed.html"
                subject = "Card Payment Confirmed - EasyGo"

            user.reminder = True            
            user.cancelled = False
            user.save()      

            if user.return_pickup_time == 'x':
                user1 = Post.objects.filter(email__iexact=user.email)[1]
                user1.cash = True if payment_method == "cash" else False
                user1.prepay = True if payment_method == "card" else False                
                user1.pending = False if payment_method == "cash" else True
                user1.reminder = True
                user1.cancelled = False
                user1.save()     

        # 6️⃣ Send email
        handle_email_sending(request, email, subject, template_name, context, getattr(user, 'email1', None))

        return render_inquiry_done(request)

    return render(request, 'basecamp/email/email_dispatch.html', {})

