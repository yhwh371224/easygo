from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def driver_impersonate(request, driver_id):
    from blog.models import Driver
    from django.contrib.auth import login

    driver = get_object_or_404(Driver, pk=driver_id)
    if not driver.user:
        return redirect('/horeb_yhwh/')

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
            return redirect('/horeb_yhwh/')
        except User.DoesNotExist:
            pass
    return redirect('/horeb_yhwh/')


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

        if len(new_password) < 8:
            error = 'Password must be at least 8 characters.'
        elif new_password != confirm:
            error = 'Passwords do not match.'
        else:
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

    # 오늘 이후 미래 트립 (날짜 + 시간 순)
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
        })

    # 정산 내역 (최신순, 최대 2개)
    settlements = list(
        DriverSettlement.objects
        .filter(driver=driver)
        .order_by('-settled_at')[:1]
    )

    last_settlement = settlements[0] if len(settlements) >= 1 else None

    # 과거 트립: last_settlement 이후 ~ today 미만
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
        past_posts = past_posts.filter(pickup_date__gt=last_settlement.settled_at.date())
    past_posts = past_posts.order_by('-pickup_date', '-pickup_time')

    # 트립과 정산을 날짜순으로 인터리브
    timeline = []
    for post in past_posts:
        timeline.append({
            'type': 'trip',
            'date': post.pickup_date,
            'data': post,
        })
    for s in settlements:
        timeline.append({
            'type': 'settlement',
            'date': s.settled_at.date(),
            'data': s,
        })
    timeline.sort(key=lambda x: x['date'], reverse=True)

    # 마지막 정산 이후 트립만 current 합계 계산
    current_total_paid = Decimal('0')
    current_total_cash = Decimal('0')

    for post in past_posts:
        try:
            amount = Decimal(str(post.price))
        except Exception:
            continue
        if post.paid:
            current_total_paid += amount
        elif post.cash:
            current_total_cash += amount

    # 오늘 이후 트립도 current 합계에 포함
    for t in trips:
        post = t['post']
        try:
            amount = Decimal(str(post.price))
        except Exception:
            continue
        if post.paid:
            current_total_paid += amount
        elif post.cash:
            current_total_cash += amount

    current_grand_total = current_total_paid + current_total_cash

    return render(request, 'basecamp/driver/dashboard.html', {
        'driver': driver,
        'trips': trips,
        'today': today,
        'timeline': timeline,
        'current_total_paid': current_total_paid,
        'current_total_cash': current_total_cash,
        'current_grand_total': current_grand_total,
        'impersonator_id': request.session.get('impersonator_id'),
    })


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
