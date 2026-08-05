import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django_ratelimit.decorators import ratelimit
from main import settings

from basecamp.modules.view_helpers import verify_turnstile, get_client_ip
from blog.bird_proxy import get_proxy_number

logger = logging.getLogger(__name__)

COMPANY_NAME = "EasyGo Airport Shuttle (Nexflow Ventures Pty Ltd)"
COMPANY_ABN  = "25 697 358 535"

CAR_TYPE_SUGGESTIONS = [
    'Sedan',
    'SUV',
    'Van / People Mover (up to 7 seats)',
    'Maxi Taxi / Minibus (8–11 seats)',
]

# Mirrors the Driver model field max_length values — checked before create()
# so a deliberately-oversized POST gets a clean form error instead of an
# unhandled DB-level "value too long" error (Postgres enforces varchar(N)).
DRIVER_APPLY_FIELD_MAX_LENGTHS = {
    'driver_name': 100, 'driver_contact': 50, 'driver_email': 254, 'driver_car': 30,
    'driver_plate': 30, 'abn': 20, 'bank_account_name': 100,
    'bank_bsb': 10, 'bank_account_number': 20, 'payid_number': 50,
}


def _is_valid_email(value):
    from django.core.validators import validate_email
    try:
        validate_email(value)
        return True
    except ValidationError:
        return False


def _build_rcti_context(settlement):
    """
    Return display-only RCTI figures for a settlement.
    Does NOT modify any stored field.
    """
    all_items = settlement.items.select_related('post').all()
    paid_items_raw = [item for item in all_items if not item.post.cash]

    rcti_items = []
    for item in paid_items_raw:
        lt = item.line_total
        item_gst = (lt / Decimal('11')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        rcti_items.append({
            'date': item.post.pickup_date,
            'description': item.description or item.post.suburb or '–',
            'amount_ex': lt - item_gst,
            'gst': item_gst,
            'line_total': lt,
        })

    paid_total = settlement.paid_total
    gst = (paid_total / Decimal('11')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return {
        'rcti_items': rcti_items,
        'rcti_gst': gst,
        'rcti_amount_ex': paid_total - gst,
        'company_name': COMPANY_NAME,
        'company_abn': COMPANY_ABN,
    }


@staff_member_required
def driver_impersonate(request, driver_id):
    from blog.models import Driver
    from django.contrib.auth import login

    driver = get_object_or_404(Driver, pk=driver_id)
    if not driver.user:
        return redirect(f'/{settings.SECRET_ADMIN_URL}/')

    impersonator_id = request.user.id
    login(request, driver.user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['impersonator_id'] = impersonator_id
    request.session.modified = True

    return redirect('blog:driver_dashboard')


@login_required(login_url='/driver/login/')
def driver_impersonate_exit(request):
    from django.contrib.auth.models import User

    impersonator_id = request.session.get('impersonator_id')
    if impersonator_id:
        try:
            superuser = User.objects.get(pk=impersonator_id)
            request.session.pop('impersonator_id', None)
            login(request, superuser, backend='django.contrib.auth.backends.ModelBackend')
            return redirect(f'/{settings.SECRET_ADMIN_URL}/')
        except User.DoesNotExist:
            pass
    return redirect(f'/{settings.SECRET_ADMIN_URL}/')


def _notify_new_driver_application(driver):
    """Best-effort email to the office when a new application comes in.

    Failure to send must never block the applicant's flow — they've already
    been saved as a pending Driver by the time this runs.
    """
    from utils.email import send_text_email
    from main.settings import RECIPIENT_EMAIL

    review_url = f"{settings.SITE_URL}/{settings.SECRET_ADMIN_URL}/blog/driver/{driver.pk}/change/"
    message = (
        "New driver application received — pending review (not active yet).\n\n"
        f"Name: {driver.driver_name}\n"
        f"Contact: {driver.driver_contact}\n"
        f"Email: {driver.driver_email}\n"
        f"Region: {driver.region}\n"
        f"Vehicle: {driver.driver_car} — plate {driver.driver_plate or 'not supplied'}\n"
        f"Licence class: {driver.get_license_class_display()} "
        f"(number not collected on the form — take it off the licence itself)\n"
        f"Licence scan attached: {'Yes' if driver.license_scan else 'No — follow up with the driver'}\n"
        f"Vehicle insurance declared: "
        f"{'Yes' if driver.has_vehicle_insurance else 'No — do not activate until covered'}\n"
        f"ABN: {driver.abn} — check GST registration on ABN Lookup and set it in the admin\n"
        f"Payment method: {driver.get_payment_method_display()}\n\n"
        f"Review and activate here:\n{review_url}\n"
    )
    try:
        send_text_email(f"[New Driver Application] {driver.driver_name}", message, [RECIPIENT_EMAIL])
    except Exception:
        logger.exception("driver_apply: failed to send admin notification for driver id=%s", driver.pk)


def _notify_driver_application_received(driver):
    """Best-effort confirmation email to the applicant themselves.

    Same "must never block the applicant's flow" reasoning as
    _notify_new_driver_application — the Driver record already exists by
    the time this runs, so a failed send here is just a missed courtesy
    email, not a broken application.
    """
    from utils.email import send_text_email

    message = (
        f"Hi {driver.driver_name},\n\n"
        "Thanks for applying to drive with EasyGo Airport Shuttle! We've received "
        "your application and it's now with our team for review. We'll be in touch "
        "soon once we've had a look.\n\n"
        "Thanks again for applying,\n"
        f"{COMPANY_NAME}\n"
    )
    try:
        send_text_email("Your EasyGo driver application has been received", message, [driver.driver_email])
    except Exception:
        logger.exception("driver_apply: failed to send applicant confirmation for driver id=%s", driver.pk)


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def driver_apply(request):
    """Public job-application form — no login required.

    Creates a Driver record with is_active=False: the account exists and the
    applicant can immediately set up a portal login and confirm the
    subcontractor agreement (see driver_apply_account / driver_agreement),
    but the driver stays out of dispatch-relevant queries (bank-payment
    auto-matching, reminder emails — see Driver.is_active usages) until
    office staff review the application and flip is_active on in the admin.
    Licence class is the only licence detail asked for — it decides what work
    the driver can be given (maxi/minibus needs LR+), so staff need it before
    any paperwork arrives. The licence number and scan are deliberately NOT
    collected here: an unverified typed number is useless, and staff capture
    both off the licence itself during review (Driver.license_number /
    license_scan are still editable in the admin).

    Also used by subcontractors (partner operators supplying their own
    vehicles/drivers) — same fields, same review. Driver.is_company is a
    staff-side flag set in the admin during review, not asked for here.
    """
    from blog.models import Driver
    from blog.models.driver import LICENSE_CLASS_CHOICES
    from regions.models import Region

    regions = Region.objects.filter(is_active=True).order_by('name')

    error = None
    form_data = {
        'driver_name': '', 'driver_contact': '', 'driver_email': '',
        'driver_car': '', 'driver_plate': '', 'license_class': '',
        'abn': '', 'has_vehicle_insurance': False, 'payment_method': '',
        'bank_account_name': '', 'bank_bsb': '', 'bank_account_number': '',
        'payid_number': '', 'region_id': '',
    }
    checkbox_fields = ('has_vehicle_insurance',)
    region = None

    if request.method == 'POST':
        for field in form_data:
            if field in checkbox_fields:
                continue
            form_data[field] = (request.POST.get(field) or '').strip()
        for field in checkbox_fields:
            form_data[field] = request.POST.get(field) == 'on'
        region = regions.filter(pk=form_data['region_id']).first() if form_data['region_id'] else None

        token = request.POST.get('cf-turnstile-response', '')
        required = ['driver_name', 'driver_contact', 'driver_email', 'driver_car',
                    'driver_plate', 'license_class', 'abn']

        if not verify_turnstile(token, get_client_ip(request)):
            error = 'Security verification failed. Please try again.'
        elif not all(form_data[f] for f in required):
            error = 'Please fill in all required fields.'
        elif any(len(form_data[f]) > limit for f, limit in DRIVER_APPLY_FIELD_MAX_LENGTHS.items()):
            error = 'One of the fields is too long — please shorten it.'
        elif form_data['license_class'] not in dict(LICENSE_CLASS_CHOICES):
            error = 'Please choose a valid licence class.'
        # Region picker disabled on the form — set manually via Django admin
        # after the applicant is created (Driver.region is nullable).
        # elif not region:
        #     error = 'Please select which region you\'ll be driving in.'
        elif not _is_valid_email(form_data['driver_email']):
            error = 'Please enter a valid email address.'
        elif form_data['payment_method'] == 'bank' and not all([
            form_data['bank_account_name'], form_data['bank_bsb'], form_data['bank_account_number'],
        ]):
            error = 'Please enter your bank account name, BSB and account number.'
        elif form_data['payment_method'] == 'payid' and not form_data['payid_number']:
            error = 'Please enter your PayID.'
        elif form_data['payment_method'] not in ('bank', 'payid'):
            error = 'Please choose how you would like to be paid.'

        if not error:
            payid_or_account = (
                form_data['payid_number'] if form_data['payment_method'] == 'payid'
                else form_data['bank_account_number']
            )
            driver = Driver.objects.create(
                driver_name=form_data['driver_name'],
                driver_contact=form_data['driver_contact'],
                driver_email=form_data['driver_email'],
                region=region,
                driver_car=form_data['driver_car'],
                driver_plate=form_data['driver_plate'],
                has_vehicle_insurance=form_data['has_vehicle_insurance'],
                license_class=form_data['license_class'],
                abn=form_data['abn'],
                payment_method=form_data['payment_method'],
                bank_account_name=form_data['bank_account_name'],
                bank_bsb=form_data['bank_bsb'],
                bank_account_number=form_data['bank_account_number'],
                payid_number=form_data['payid_number'],
                payment_match_digits=re.sub(r'\D', '', payid_or_account),
                is_active=False,
                application_submitted_at=timezone.now(),
            )
            request.session['pending_driver_id'] = driver.pk
            _notify_new_driver_application(driver)
            _notify_driver_application_received(driver)
            return redirect('blog:driver_apply_account')

    return render(request, 'basecamp/driver/apply.html', {
        'error': error,
        'form_data': form_data,
        'license_classes': LICENSE_CLASS_CHOICES,
        'car_type_suggestions': CAR_TYPE_SUGGESTIONS,
        'regions': regions,
    })


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def driver_apply_account(request):
    """Step 2 of the public application: applicant sets their own portal
    username/password, right after driver_apply creates the pending Driver.

    Only reachable via the pending_driver_id stashed in session by
    driver_apply — this is not a general "create a driver account" endpoint.
    Once the User is created and linked, the applicant is logged straight
    into the subcontractor agreement page.
    """
    from blog.models import Driver

    driver_id = request.session.get('pending_driver_id')
    if not driver_id:
        return redirect('blog:driver_apply')
    driver = get_object_or_404(Driver, pk=driver_id)
    if driver.user:
        request.session.pop('pending_driver_id', None)
        return redirect('blog:driver_login')

    error = None
    username = ''

    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')

        if not username:
            error = 'Please choose a username.'
        elif User.objects.filter(username__iexact=username).exists():
            error = 'That username is already taken.'
        elif password != confirm:
            error = 'Passwords do not match.'
        else:
            try:
                validate_password(password)
            except ValidationError as e:
                error = ' '.join(e.messages)

        if not error:
            user = User.objects.create_user(
                username=username, password=password, email=driver.driver_email or '',
            )
            driver.user = user
            driver.must_change_password = False
            driver.save(update_fields=['user', 'must_change_password'])
            request.session.pop('pending_driver_id', None)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('blog:driver_agreement')

    return render(request, 'basecamp/driver/apply_account.html', {
        'error': error, 'driver': driver, 'username': username,
    })


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def driver_login(request):
    if request.user.is_authenticated:
        try:
            if request.user.driver:
                return redirect('blog:driver_dashboard')
        except Exception:
            pass

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                driver = user.driver
            except Exception:
                error = 'No driver account is linked to this user.'
                return render(request, 'basecamp/driver/login.html', {'error': error})
            login(request, user)
            request.session.set_expiry(60 * 60 * 24)
            if driver.must_change_password:
                return redirect('blog:driver_change_password')
            return redirect('blog:driver_dashboard')
        else:
            error = 'Incorrect username or password.'

    return render(request, 'basecamp/driver/login.html', {'error': error})


@login_required(login_url='/driver/login/')
def driver_change_password(request):
    try:
        driver = request.user.driver
    except Exception:
        return redirect('blog:driver_login')

    error = None
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        confirm = request.POST.get('confirm_password', '').strip()

        if new_password != confirm:
            error = 'Passwords do not match.'
        else:
            try:
                validate_password(new_password, request.user)
            except ValidationError as e:
                error = ' '.join(e.messages)
        if not error:
            request.user.set_password(new_password)
            request.user.save()
            driver.must_change_password = False
            driver.save()
            user = authenticate(request, username=request.user.username, password=new_password)
            if user:
                login(request, user)
            return redirect('blog:driver_dashboard')

    return render(request, 'basecamp/driver/change_password.html', {'error': error})


@login_required(login_url='/driver/login/')
def driver_password_change(request):
    try:
        driver = request.user.driver
    except Exception:
        return redirect('blog:driver_login')

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('blog:driver_dashboard')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'basecamp/driver/driver_password_change.html', {'form': form, 'driver': driver})


@require_POST
def driver_logout(request):
    logout(request)
    return redirect('blog:driver_login')


@login_required(login_url='/driver/login/')
def driver_dashboard(request):
    try:
        driver = request.user.driver
    except Exception:
        return redirect('blog:driver_login')

    from blog.models import Post, DriverSettlement
    today = timezone.localdate()
    now = timezone.now()
    tomorrow = today + timedelta(days=1)

    # 대시보드 표시용 오늘 이후 트립 (use_proxy=True 인 것만)
    posts = (
        Post.objects
        .filter(
            driver=driver,
            pickup_date__gte=today,
            cancelled=False,
            use_proxy=True,
        )
        .order_by('pickup_date', 'pickup_time')
    )

    # 밸런스용 오늘~내일까지 트립 (완료 포함, use_proxy 무관) - 모레 이후 제외
    balance_posts_today = (
        Post.objects
        .filter(
            driver=driver,
            pickup_date__gte=today,
            pickup_date__lt=today + timedelta(days=2),
            cancelled=False,
        )
        .exclude(price__isnull=True)
        .exclude(price='')
    )

    trips = []
    for post in posts:
        try:
            pickup_naive = datetime.strptime(
                f'{post.pickup_date} {post.pickup_time or "00:00"}',
                '%Y-%m-%d %H:%M'
            )
            pickup_dt = timezone.make_aware(pickup_naive)
        except Exception:
            pickup_dt = None

        is_past = pickup_dt and (pickup_dt + timedelta(hours=3) < now)
        # Full detail (street + live proxy number) only opens up the day
        # before pickup and on the day itself — see _get_active_mapping()
        # in bird_webhooks.py, which enforces the same window on the actual
        # call/SMS bridging. Before that, the trip is visible (so the driver
        # can plan around it) but shows suburb-only and a placeholder number.
        in_window = post.pickup_date in (today, tomorrow)
        trips.append({
            'post': post,
            'pickup_dt': pickup_dt,
            'is_past': is_past,
            'in_window': in_window,
            # Same resolver the customer's email uses, so the driver is never
            # told to ring a number the customer was never given. Outside the
            # window there's nothing live to show — BIRD_NUMBER is a real,
            # routable number, and showing it here risks the driver dialling
            # it and reaching an unrelated in-window booking that also falls
            # back to it (see _get_driver_target in bird_webhooks.py).
            'proxy_number': get_proxy_number(post, driver) if in_window else None,
        })

    # 정산 내역 (최신순, 최대 2개)
    settlements = list(
        DriverSettlement.objects
        .filter(driver=driver)
        .order_by('-settled_at')[:2]
    )

    last_settlement = settlements[0] if len(settlements) >= 1 else None
    second_last_settlement = settlements[1] if len(settlements) >= 2 else None

    # 계산용 past_posts: last_settlement 이후 ~ today 미만
    past_posts = (
        Post.objects
        .filter(
            driver=driver,
            pickup_date__lt=today,
            cancelled=False,
        )
        .exclude(price__isnull=True)
        .exclude(price='')
    )
    if last_settlement:
        past_posts = past_posts.filter(pickup_date__gt=last_settlement.to_date)
    past_posts = past_posts.order_by('-pickup_date', '-pickup_time')

    # timeline용 posts: second_last_settlement 이후 ~ today 미만 (히스토리 표시용)
    timeline_posts = (
        Post.objects
        .filter(
            driver=driver,
            pickup_date__lt=today,
            cancelled=False,
        )
        .exclude(price__isnull=True)
        .exclude(price='')
    )
    if second_last_settlement:
        timeline_posts = timeline_posts.filter(pickup_date__gt=second_last_settlement.to_date)
    if last_settlement:  # ← 이거 추가
        timeline_posts = timeline_posts.exclude(pickup_date=last_settlement.to_date)
    timeline_posts = timeline_posts.order_by('-pickup_date', '-pickup_time')

    # 트립과 정산을 날짜순으로 인터리브
    timeline = []
    for post in timeline_posts:
        timeline.append({
            'type': 'trip',
            'date': post.pickup_date,
            'data': post,
        })
    for s in settlements:
        timeline.append({
            'type': 'settlement',
            'date': s.to_date,
            'data': s,
        })

    # 오늘 완료된 잡 (use_proxy=False, 대시보드에 표시 안 되지만 timeline엔 표시)
    completed_today = (
        Post.objects
        .filter(
            driver=driver,
            pickup_date=today,
            cancelled=False,
            use_proxy=False,
        )
        .exclude(price__isnull=True)
        .exclude(price='')
    )
    for post in completed_today:
        timeline.append({
            'type': 'trip',
            'date': post.pickup_date,
            'data': post,
        })
    timeline.sort(key=lambda x: x['date'], reverse=True)

    # 마지막 정산 이후 트립만 합계 계산
    current_total_paid = Decimal('0')
    current_total_cash = Decimal('0')
    to_be_paid = Decimal('0')
    to_be_cash = Decimal('0')

    for post in past_posts:
        try:
            amount = Decimal(str(post.driver_price))
        except Exception:
            continue
        # Driver bears their share of any customer refund on this trip.
        amount -= (post.driver_refund_deduction or Decimal('0'))
        if post.cash:
            current_total_cash += amount
        elif post.paid:
            current_total_paid += amount
        if not last_settlement or post.pickup_date > last_settlement.to_date:
            if post.cash:
                to_be_cash += amount
            elif post.paid:
                to_be_paid += amount

    for post in balance_posts_today:
        try:
            amount = Decimal(str(post.driver_price))
        except Exception:
            continue
        # Driver bears their share of any customer refund on this trip.
        amount -= (post.driver_refund_deduction or Decimal('0'))
        if post.cash:
            current_total_cash += amount
        elif post.paid:
            current_total_paid += amount
        if not last_settlement or post.pickup_date > last_settlement.to_date:
            if post.cash:
                to_be_cash += amount
            elif post.paid:
                to_be_paid += amount

    current_grand_total = current_total_paid + current_total_cash

    # 예정 금액: 모레 이후 트립 중 배정+proxy 연결된 것만 (아직 정산 대상 아님, 참고용 별도 라인)
    pending_posts = (
        Post.objects
        .filter(
            driver=driver,
            pickup_date__gte=today + timedelta(days=2),
            cancelled=False,
            use_proxy=True,
        )
        .exclude(price__isnull=True)
        .exclude(price='')
    )
    pending_total = Decimal('0')
    for post in pending_posts:
        try:
            amount = Decimal(str(post.driver_price))
        except Exception:
            continue
        amount -= (post.driver_refund_deduction or Decimal('0'))
        pending_total += amount

    agreement_confirmed = _confirmed_agreement(driver) is not None

    return render(request, 'basecamp/driver/dashboard.html', {
        'driver': driver,
        'trips': trips,
        'today': today,
        'timeline': timeline,
        'agreement_confirmed': agreement_confirmed,
        'current_total_paid': current_total_paid,
        'current_total_cash': current_total_cash,
        'current_grand_total': current_grand_total,
        'to_be_paid': to_be_paid,
        'pending_total': pending_total,
        'impersonator_id': request.session.get('impersonator_id'),
    })


@login_required(login_url='/driver/login/')
def driver_settlement_list(request):
    try:
        driver = request.user.driver
    except Exception:
        return redirect('blog:driver_login')

    from blog.models import DriverSettlement
    settlements = DriverSettlement.objects.filter(driver=driver).order_by('-settled_at')
    return render(request, 'basecamp/driver/driver_settlement_list.html', {
        'driver': driver,
        'settlements': settlements,
        'impersonator_id': request.session.get('impersonator_id'),
    })


@login_required(login_url='/driver/login/')
def driver_settlement_detail(request, settlement_number):
    try:
        driver = request.user.driver
    except Exception:
        return redirect('blog:driver_login')

    from blog.models import DriverSettlement
    settlement = get_object_or_404(DriverSettlement, settlement_number=settlement_number)
    if settlement.driver != driver:
        raise Http404

    ctx = {
        'driver': driver,
        'settlement': settlement,
        'impersonator_id': request.session.get('impersonator_id'),
        'is_pdf': False,
    }
    if settlement.status == 'paid':
        ctx.update(_build_rcti_context(settlement))
    return render(request, 'basecamp/driver/driver_settlement_detail.html', ctx)


@login_required(login_url='/driver/login/')
def driver_settlement_pdf(request, settlement_number):
    try:
        driver = request.user.driver
    except Exception:
        return redirect('blog:driver_login')

    from blog.models import DriverSettlement
    settlement = get_object_or_404(DriverSettlement, settlement_number=settlement_number)
    if settlement.driver != driver:
        raise Http404
    if settlement.status != 'paid':
        raise Http404

    from weasyprint import HTML
    ctx = {'driver': driver, 'settlement': settlement, 'is_pdf': True}
    ctx.update(_build_rcti_context(settlement))
    html_string = render_to_string('basecamp/driver/driver_settlement_detail.html', ctx)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="{settlement.settlement_number}.pdf"'
    )
    return response


def _confirmed_agreement(driver):
    """The driver's acknowledgement of the current agreement version, if any.

    Deliberately only asks "is there a confirmed row for this version": a
    driver who has already signed is never re-prompted on their own, even if
    the items they'd be shown today differ (e.g. staff turned GST on
    afterwards). Re-collecting consent is a manual call — delete the
    DriverAgreement row in the admin and send them the agreement link.
    The dashboard's "Action required" banner keys off this too.
    """
    from blog.models import DriverAgreement, CURRENT_AGREEMENT_VERSION

    return DriverAgreement.objects.filter(
        driver=driver,
        version=CURRENT_AGREEMENT_VERSION,
        confirmed_at__isnull=False,
    ).first()


def _agreement_items(driver):
    """The summary items shown on the agreement page.

    Wording branches on ``driver.is_company``: individual owner-drivers
    confirm things in the first person ("I..."), while partner companies
    that supply drivers (e.g. a depot/fleet operator) confirm on behalf of
    their business ("Our company...") — an office contact at that company
    can't truthfully tick "I hold the insurance" or "I am responsible for
    my own vehicle" since they're not the one driving.
    """
    if driver.is_company:
        return [
            {
                'field': 'item_status_confirmed',
                'title': 'Independent contractor, not an agent',
                'detail': (
                    "Our company operates as an independent business supplying "
                    f"driver and vehicle services to {COMPANY_NAME}, not as its "
                    "agent. Our company is responsible for engaging, "
                    "managing and paying our own drivers, and for their vehicles, "
                    "licences and registrations."
                ),
            },
            {
                'field': 'item_liability_confirmed',
                'title': 'Our responsibility',
                'detail': (
                    "Our company holds the required insurance covering our drivers and "
                    "vehicles while performing work for "
                    f"{COMPANY_NAME}, and is responsible for any damage, "
                    "injury or liability arising from the conduct "
                    "of our drivers or vehicles, including anything that occurs "
                    "between pickup and drop-off."
                ),
            },
        ]

    items = [
        {
            'field': 'item_status_confirmed',
            'title': 'Independent subcontractor, not an employee',
            'detail': (
                "I operate my own business and provide services to "
                f"{COMPANY_NAME} as an independent subcontractor, not as an "
                "employee. I am responsible for my own vehicle, licences, "
                "registration and running costs."
            ),
        },
        {
            'field': 'item_liability_confirmed',
            'title': 'My responsibility',
            'detail': (
                "I hold the insurances required to carry passengers for hire "
                "and reward, and I am responsible for any damage or "
                "liability arising from my own driving and vehicle, including "
                "anything that occurs between pickup and drop-off."
            ),
        },
    ]

    # RCTIs only carry GST for drivers registered for it (see
    # settlement_service.py), so the item is meaningless — and only confusing
    # — for a driver who isn't GST-registered.
    if driver.gst_registered:
        items.append({
            'field': 'item_rcti_confirmed',
            'title': 'Invoices & payment receipts',
            'detail': (
                f"I agree that {COMPANY_NAME} (ABN {COMPANY_ABN}) may issue "
                "Recipient Created Tax Invoices (RCTIs) for the services I "
                "supply, so I do not need to issue my own invoices for those "
                "services. Each time a payment is made, the invoice / receipt "
                "for it is emailed to the address I give below."
            ),
        })

    # Only a driver with an ABN can issue their own tax invoice at all — a
    # driver without one always gets an RCTI, so the choice doesn't apply.
    if driver.abn:
        items.append({
            'field': 'item_tax_invoice_confirmed',
            'title': 'Tax invoice or RCTI',
            'detail': (
                "You may issue EasyGo a tax invoice for your services "
                "provided; otherwise, EasyGo will issue you a Recipient "
                "Created Tax Invoice (RCTI) on your behalf."
            ),
        })

    return items


def _handle_agreement(request, driver):
    """Shared GET/POST handling for the subcontractor agreement page.

    Used both by the logged-in portal page and by the no-login token link,
    so a subcontractor without dashboard credentials yet can still review
    and confirm. GET renders the summary items for this driver/company
    (expand-on-click detail — see :func:`_agreement_items`). POST records a
    :class:`DriverAgreement` once every item shown is ticked and the company
    name/ABN/invoice email are filled in. Nothing here ever touches the
    accounting app.
    """
    from blog.models import DriverAgreement, CURRENT_AGREEMENT_VERSION
    from basecamp.modules.view_helpers import get_client_ip

    version = CURRENT_AGREEMENT_VERSION

    existing = _confirmed_agreement(driver)

    items = _agreement_items(driver)

    if request.method == 'POST':
        # Already confirmed — treat a re-submit as a no-op (idempotent link).
        if existing:
            return render(request, 'basecamp/driver/agreement_done.html', {
                'driver': driver, 'version': version, 'agreement': existing,
            })

        company_name = (request.POST.get('company_name') or '').strip()
        abn = (request.POST.get('abn') or '').strip()
        invoice_email = (request.POST.get('invoice_email') or '').strip()
        signed_by_name = (request.POST.get('signed_by_name') or '').strip()
        signed_by_title = (request.POST.get('signed_by_title') or '').strip()
        all_checked = all(request.POST.get(item['field']) == 'on' for item in items)

        error = None
        if not company_name or not abn:
            error = 'Please enter your company name and ABN.'
        elif not invoice_email:
            error = 'Please enter the email address your invoices should go to.'
        elif not _is_valid_email(invoice_email):
            error = 'Please enter a valid email address for your invoices.'
        elif driver.is_company and (not signed_by_name or not signed_by_title):
            error = 'Please enter your name and title/position.'
        elif not all_checked:
            error = 'Please tick all the boxes above before confirming.'

        if error:
            return render(request, 'basecamp/driver/agreement.html', {
                'driver': driver,
                'version': version,
                'items': items,
                'company_name': company_name,
                'abn': abn,
                'invoice_email': invoice_email,
                'signed_by_name': signed_by_name,
                'signed_by_title': signed_by_title,
                'error': error,
            })

        # Subcontractor enters their own registered details — trusted as the
        # source of truth over whatever admin may have typed in previously.
        # The invoice address is the one they just agreed their RCTIs go to,
        # so it becomes the driver's contact email outright.
        driver.business_name = company_name
        driver.abn = abn
        driver.driver_email = invoice_email
        driver.save(update_fields=['business_name', 'abn', 'driver_email'])

        agreement, _ = DriverAgreement.objects.get_or_create(
            driver=driver, version=version,
        )
        # Only the items actually shown/ticked apply — a driver who isn't
        # GST-registered never sees the RCTI item, so item_rcti_confirmed
        # stays False for them.
        for item in items:
            setattr(agreement, item['field'], True)
        if driver.is_company:
            agreement.signed_by_name = signed_by_name
            agreement.signed_by_title = signed_by_title
        agreement.confirmed_at = timezone.now()
        agreement.ip_address = get_client_ip(request)
        agreement.gst_registered_snapshot = driver.gst_registered
        agreement.save()

        return render(request, 'basecamp/driver/agreement_done.html', {
            'driver': driver, 'version': version, 'agreement': agreement,
        })

    if existing:
        return render(request, 'basecamp/driver/agreement_done.html', {
            'driver': driver, 'version': version, 'agreement': existing,
        })

    return render(request, 'basecamp/driver/agreement.html', {
        'driver': driver,
        'version': version,
        'items': items,
        'company_name': driver.business_name or '',
        'abn': driver.abn or '',
        'invoice_email': driver.driver_email or '',
        'signed_by_name': '',
        'signed_by_title': '',
        'error': None,
    })


@login_required(login_url='/driver/login/')
def driver_agreement(request):
    """Driver portal page where the logged-in driver reviews and confirms the
    subcontractor agreement."""
    try:
        driver = request.user.driver
    except Exception:
        return redirect('blog:driver_login')
    return _handle_agreement(request, driver)


def driver_agreement_public(request, token):
    """No-login link for confirming the subcontractor agreement.

    Sent directly to a subcontractor so they can review and confirm before
    (or without ever needing) a portal login — dashboard access can be set
    up separately afterwards. Looked up by the driver's private
    ``agreement_token``, not by session, so it deliberately does not grant
    any further portal access beyond this one page.
    """
    from blog.models import Driver
    driver = get_object_or_404(Driver, agreement_token=token)
    return _handle_agreement(request, driver)


@login_required(login_url='/driver/login/')
@require_POST
def driver_complete_trip(request, post_id):
    try:
        driver = request.user.driver
    except Exception:
        return JsonResponse({'ok': False, 'error': 'No driver account linked.'}, status=403)

    from blog.models import Post
    from blog.bird_proxy import close_bird_mapping

    post = get_object_or_404(Post, pk=post_id, driver=driver)
    ok = close_bird_mapping(post)

    return JsonResponse({'ok': ok})
