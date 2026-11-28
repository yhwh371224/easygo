import logging

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required

from django.db.models import Q

from regions.models import Region, RegionSuburb
from regions.models import Terminal
from basecamp.area import get_suburbs, get_carousel_suburbs
from basecamp.area_zones import area_zones
from basecamp.basecamp_utils import get_sorted_suburbs
from articles.models import Post
from regions.models.airport import CruiseTerminal

logger = logging.getLogger(__name__)


def _build_pillar_context(suburb_obj, zone_info):
    name = suburb_obj.name
    return {
        'suburb': name,
        'details': suburb_obj,
        'area_type': suburb_obj.zone,
        'main_suburbs': zone_info.get('main_suburbs', [name]),
        'title': zone_info.get('title', '').format(suburb=name),
        'meta_description': zone_info.get('meta_description', '').format(suburb=name),
        'h1': zone_info.get('h1', '').format(suburb=name),
        'h2': zone_info.get('h2', ''),
        'route_info': zone_info.get('route_info', '').format(suburb=name),
        'landmarks': zone_info.get('landmark', ''),
    }


def home(request):
    carousel_suburbs = get_carousel_suburbs()
    region = get_object_or_404(Region, slug='sydney', is_active=True)
    home_suburbs = region.suburbs.filter(is_active=True).order_by('-is_pinned', 'sort_order', 'name')
    airport_terminals = Terminal.objects.filter(
        airport__in=region.airports.all()
    ).select_related("airport")
    cruise_terminals = CruiseTerminal.objects.filter(region=region)
    latest_post = (
        Post.objects
        .filter(status='published')
        .filter(Q(regions__isnull=True) | Q(regions__slug='sydney'))
        .order_by('-created_at')
        .distinct()
        .first()
    )

    return render(request, 'basecamp/home.html', {
        'carousel_suburbs': carousel_suburbs,
        'home_suburbs': home_suburbs,
        'airport_terminals': airport_terminals,
        'cruise_terminals': cruise_terminals,
        'latest_post': latest_post,
    })



# 대표 페이지(/maxi-taxi/)에서 링크하는 6곳만 수버브 페이지를 남긴다. 나머지 380여 개는
# 3개월 클릭 24회라 2026-11-24 에 /maxi-taxi/ 로 301 — 찍어낸 페이지 수를 줄이고 링크 가치를
# 대표 페이지로 모은다. 남긴 6곳은 검색에도 나오게 한다(noindex 해제, sitemap 포함).
MAXI_TAXI_SUBURBS = {'chatswood', 'hornsby', 'parramatta', 'blacktown', 'hotels-in-cbd', 'lindfield'}
MAXI_TAXI_SLUG_ALIASES = {'hotels-in-city': 'hotels-in-cbd'}  # 예전 링크 주소


def maxi_taxi_legacy(request, suburb):
    """/maxi_taxi/<suburb>/ → 최종 주소로 한 번에 (301 이 두 번 이어지지 않게)."""
    slug = MAXI_TAXI_SLUG_ALIASES.get(suburb.lower(), suburb.lower())
    if slug in MAXI_TAXI_SUBURBS:
        return redirect('basecamp:maxi_taxi_suburb', suburb=slug, permanent=True)
    return redirect('basecamp:maxi_taxi_hyphen', permanent=True)


def maxi_taxi(request, suburb=None):
    if not suburb:
        from easygo_review.review_region import cached_service_reviews
        return render(request, 'basecamp/pillars/maxi-taxi-pillar.html', {
            'reviews': cached_service_reviews('group', 'sydney'),
            'reviews_title': 'What groups of 7–13 say',
        })

    slug = MAXI_TAXI_SLUG_ALIASES.get(suburb.lower(), suburb.lower())
    if slug not in MAXI_TAXI_SUBURBS:
        return redirect('basecamp:maxi_taxi_hyphen', permanent=True)
    if slug != suburb:
        return redirect('basecamp:maxi_taxi_suburb', suburb=slug, permanent=True)

    suburb_obj = RegionSuburb.objects.filter(
        region__slug='sydney', slug=slug, is_active=True,
    ).first()
    if not suburb_obj:
        return redirect('basecamp:maxi_taxi_hyphen', permanent=True)

    zone_info = area_zones.get(suburb_obj.zone, {})
    context = _build_pillar_context(suburb_obj, zone_info)
    context['landmark'] = context['landmarks']
    context['page_bg'] = 'basecamp/photos/bg-pattern02.webp'
    return render(request, 'basecamp/pillars/airport-maxi-taxi.html', context)


def more_suburbs(request):
    suburbs = RegionSuburb.objects.filter(
        region__slug='sydney', is_active=True,
    ).order_by('name')
    return render(request, 'basecamp/layouts/more_suburbs.html', {'more_suburbs': suburbs})


def more_suburbs1(request):
    suburbs = RegionSuburb.objects.filter(
        region__slug='sydney', is_active=True,
    ).order_by('name')
    return render(request, 'basecamp/layouts/more_suburbs1.html', {'more_suburbs': suburbs})


def more_suburbs_maxi_taxi(request):
    # 수버브별 maxi-taxi 페이지를 없애면서 그 목록 페이지도 대표 페이지로 합쳤다.
    return redirect('basecamp:maxi_taxi_hyphen', permanent=True)


def booking(request):
    return redirect('/sydney/inquiry/', permanent=True)


@login_required
def confirmation(request):
    return render(request, 'basecamp/booking/confirmation.html', {
        'home_suburbs': get_sorted_suburbs(),
        'ADMIN_URL': settings.SECRET_ADMIN_URL,
    })


def inquiry(request):
    return render(request, 'basecamp/booking/inquiry.html', {
        'home_suburbs': get_sorted_suburbs(),
        'direction': 'Drop off to Domestic Airport',
    })


def inquiry1(request):
    return render(request, 'basecamp/booking/inquiry.html', {
        'pickup_date': None,
        'direction': 'Drop off to Domestic Airport',
        'suburb': None,
        'no_of_passenger': None,
    })


def payonline(request):
    """Card payment page (Stripe). Links from emails / redirects prefill it
    with ?name=&email=&amount=; the form posts to payonline_checkout."""
    # settings.ONLINE_PAYMENT_PROVIDER (.env) picks Stripe or PayPal.
    if settings.ONLINE_PAYMENT_PROVIDER != 'stripe':
        target = reverse('basecamp:payonline_paypal')
        qs = request.GET.urlencode()
        return redirect(f'{target}?{qs}' if qs else target)
    return render(request, 'basecamp/payments/payonline.html', {
        'name': (request.GET.get('name') or '').strip()[:100],
        'email': (request.GET.get('email') or '').strip()[:254],
        'amount': (request.GET.get('amount') or '').strip()[:12],
    })


def payonline_paypal(request):
    """The previous PayPal checkout page, kept as an alternative to Stripe."""
    from accounting.conf import paypal_surcharge_rate
    return render(request, 'basecamp/payments/payonline_paypal.html', {
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
        # Plain string for JS — str(Decimal) keeps it locale-free ('1.0195').
        'paypal_surcharge_factor': str(1 + paypal_surcharge_rate()),
    })
