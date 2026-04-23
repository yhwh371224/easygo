from datetime import datetime, timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
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

    impersonator_id = request.user.id  # 먼저 저장
    login(request, driver.user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['impersonator_id'] = impersonator_id  # login() 후에 세션에 저장
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
            # 첫 로그인이면 비밀번호 변경 페이지로 강제 이동
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
            # 비밀번호 변경 후 재로그인
            user = authenticate(request, username=request.user.username, password=new_password)
            if user:
                login(request, user)
            return redirect('blog:driver_dashboard')

    return render(request, 'basecamp/driver/change_password.html', {'error': error})


def driver_logout(request):
    logout(request)
    return redirect('blog:driver_login')


@login_required(login_url='/driver/login/')
def driver_dashboard(request):
    try:
        driver = request.user.driver
    except Exception:
        return redirect('blog:driver_login')

    from blog.models import Post
    today = timezone.localdate()
    now = timezone.now()

    posts = (
        Post.objects
        .filter(
            driver=driver,
            pickup_date=today,
            cancelled=False,
        )
        .exclude(contact__isnull=True)
        .exclude(contact='')
        .order_by('pickup_time')
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

    return render(request, 'basecamp/driver/dashboard.html', {
        'driver': driver,
        'trips': trips,
        'today': today,
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