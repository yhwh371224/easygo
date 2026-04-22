from datetime import datetime, timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST


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
                error = '드라이버 계정이 연결되어 있지 않습니다.'
                return render(request, 'basecamp/driver/login.html', {'error': error})
            login(request, user)
            return redirect('blog:driver_dashboard')
        else:
            error = '아이디 또는 비밀번호가 올바르지 않습니다.'

    return render(request, 'basecamp/driver/login.html', {'error': error})


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
        return JsonResponse({'ok': False, 'error': 'no driver'}, status=403)

    from blog.models import Post
    from blog.bird_proxy import close_bird_mapping

    post = get_object_or_404(Post, pk=post_id, driver=driver)
    ok = close_bird_mapping(post)

    return JsonResponse({'ok': ok})
