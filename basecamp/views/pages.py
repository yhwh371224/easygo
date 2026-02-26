from django.shortcuts import render
from django.conf import settings


def about_us(request): 
    # send_notice_email.delay('about_us accessed', 'about_us accessed', RECIPIENT_EMAIL)
    return render(request, 'basecamp/pages/about_us.html')

def arrival_guide(request): 
    return render(request, 'basecamp/pages/arrival_guide.html')

def confirmation_multiplebookings(request): 
    return render(request, 'basecamp/confirmation_multiplebookings.html')

def confirm_booking(request): 
    return render(request, 'basecamp/booking/confirm_booking.html')

def contact_form(request):
    return render(request, 'basecamp/pages/contact_form.html')

def cruise_booking(request):
    return render(request, 'basecamp/booking/cruise_booking.html')

def cruise_inquiry(request):
    return render(request, 'basecamp/booking/cruise_inquiry.html')

def error(request): 
    return render(request, 'basecamp/error/error.html')

def email_dispatch(request): 
    return render(request, 'basecamp/email/email_dispatch.html')

def email_error_confirmbooking(request): 
    return render(request, 'basecamp/email/email_error_confirmbooking.html')

def home_error(request): 
    return render(request, 'basecamp/error/home_error.html')

def inquiry_done(request):
    return render(request, 'basecamp/inquiry_done.html', {
        'google_review_url': settings.GOOGLE_REVIEW_URL,
    })

def information(request): 
    return render(request, 'basecamp/pages/information.html')

def invoice(request): 
    return render(request, 'basecamp/invoice.html')

def invoice_details(request): 
    return render(request, 'basecamp/invoice_details.html')

def meeting_point(request): 
    return render(request, 'basecamp/pages/meeting_point.html')

def payment_cancel(request): 
    return render(request, 'basecamp/payments/payment_cancel.html')

def payment_options(request):
    return render(request, 'basecamp/payments/payment_options.html')

def payment_options1(request): 
    return render(request, 'basecamp/payments/payment_options1.html')

def p2p(request):     
    return render(request, 'basecamp/booking/p2p.html')

def p2p_booking(request):
    return render(request, 'basecamp/booking/p2p_booking.html')

def p2p_single(request):
    return render(request, 'basecamp/booking/p2p_single.html')

def privacy(request):     
    return render(request, 'basecamp/pages/privacy.html')

def return_cruise_fields(request): 
    return render(request, 'basecamp/layouts/return_cruise_fields.html')

def return_flight_fields(request): 
    return render(request, 'basecamp/layouts/return_flight_fields.html')

def return_trip(request): 
    return render(request, 'basecamp/booking/return_trip.html')

def sending_email_first(request): 
    return render(request, 'basecamp/email/sending_email_first.html')

def sending_email_second(request): 
    return render(request, 'basecamp/email/sending_email_second.html')


def sending_email_input_data(request): 
    return render(request, 'basecamp/email/sending_email_input_data.html')


def service(request):     
    return render(request, 'basecamp/pages/service.html')


def success(request): 
    return render(request, 'basecamp/layouts/success.html')


def sydney_airport_shuttle(request):
    return render(request, 'basecamp/pillars/sydney_airport_shuttle.html')


def sydney_airport_transfer(request):
    return render(request, 'basecamp/pillars/sydney_airport_transfer.html')


def sydney_cruise_transfer(request):
    return render(request, 'basecamp/pillars/sydney_cruise_transfer.html')


def terms(request): 
    return render(request, 'basecamp/pages/terms.html')


def wrong_date_today(request): 
    return render(request, 'basecamp/error/wrong_date_today.html')