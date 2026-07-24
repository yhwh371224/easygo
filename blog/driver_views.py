from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
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

from blog.bird_proxy import get_proxy_number

COMPANY_NAME = "EasyGo Airport Shuttle (Nexflow Ventures Pty Ltd)"
COMPANY_ABN  = "25 697 358 535"


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
        trips.append({
            'post': post,
            'pickup_dt': pickup_dt,
            'is_past': is_past,
            # Same resolver the customer's email uses, so the driver is never
            # told to ring a number the customer was never given.
            'proxy_number': get_proxy_number(post, driver),
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

    from blog.models import DriverAgreement, CURRENT_AGREEMENT_VERSION
    agreement_confirmed = DriverAgreement.objects.filter(
        driver=driver,
        version=CURRENT_AGREEMENT_VERSION,
        confirmed_at__isnull=False,
    ).exists()

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


def _agreement_items(driver):
    """The three summary items shown on the agreement page.

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
            'title': 'Tax Invoice (RCTI)',
            'detail': (
                f"I agree that {COMPANY_NAME} (ABN {COMPANY_ABN}) may issue "
                "Tax Invoices (RCTIs) for the services I "
                "supply, and that I will not issue my own tax invoices for "
                "those services."
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
    name/ABN are filled in. Nothing here ever touches the accounting app.
    """
    from blog.models import DriverAgreement, CURRENT_AGREEMENT_VERSION
    from basecamp.modules.view_helpers import get_client_ip

    version = CURRENT_AGREEMENT_VERSION

    existing = (
        DriverAgreement.objects
        .filter(driver=driver, version=version, confirmed_at__isnull=False)
        .first()
    )

    items = _agreement_items(driver)

    if request.method == 'POST':
        # Already confirmed — treat a re-submit as a no-op (idempotent link).
        if existing:
            return render(request, 'basecamp/driver/agreement_done.html', {
                'driver': driver, 'version': version, 'agreement': existing,
            })

        company_name = (request.POST.get('company_name') or '').strip()
        abn = (request.POST.get('abn') or '').strip()
        signed_by_name = (request.POST.get('signed_by_name') or '').strip()
        signed_by_title = (request.POST.get('signed_by_title') or '').strip()
        all_checked = all(request.POST.get(item['field']) == 'on' for item in items)

        error = None
        if not company_name or not abn:
            error = 'Please enter your company name and ABN.'
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
                'signed_by_name': signed_by_name,
                'signed_by_title': signed_by_title,
                'error': error,
            })

        # Subcontractor enters their own registered details — trusted as the
        # source of truth over whatever admin may have typed in previously.
        driver.business_name = company_name
        driver.abn = abn
        driver.save(update_fields=['business_name', 'abn'])

        agreement, _ = DriverAgreement.objects.get_or_create(
            driver=driver, version=version,
        )
        # Only the items actually shown/ticked apply — the company flow has
        # no RCTI item, so item_rcti_confirmed stays False for those.
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
