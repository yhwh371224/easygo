"""shuttle/transfer 합치기 + 동네 후기 (regions/suburb_merge.py). 기본은 꺼져 있다."""

import datetime
from unittest.mock import patch

from django.core.cache import cache
from django.template import Context, Template
from django.test import TestCase, override_settings

from regions.models import Region, RegionSuburb
from regions.suburb_merge import sitemap_services, suburb_url


def region(slug, name):
    r, _ = Region.objects.get_or_create(slug=slug, defaults={
        'name': name, 'timezone': 'Australia/Sydney', 'phone': '0200000000', 'is_active': True})
    Region.objects.filter(pk=r.pk).update(is_active=True, is_coming_soon=False)
    return r


class SuburbMergeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.syd = region('sydney', 'Sydney')
        self.mel = region('melbourne', 'Melbourne')
        for reg, slug, name in [(self.syd, 'penrith', 'Penrith'), (self.syd, 'hornsby', 'Hornsby'),
                                (self.syd, 'box-hill', 'Box Hill'), (self.mel, 'werribee', 'Werribee')]:
            RegionSuburb.objects.get_or_create(region=reg, slug=slug,
                                               defaults={'name': name, 'price': 100, 'is_active': True})

    def get(self, url):
        return self.client.get(url, secure=True)

    def test_off_by_default_both_pages_served(self):
        for url in ['/sydney/airport-shuttle/penrith/', '/sydney/airport-transfer/penrith/',
                    '/melbourne/airport-transfer/werribee/']:
            self.assertEqual(self.get(url).status_code, 200, url)
        self.assertEqual(sitemap_services('sydney', 'penrith'), ('shuttle', 'transfer'))
        self.assertEqual(suburb_url('sydney', 'penrith', 'shuttle'), '/sydney/airport-shuttle/penrith/')

    @override_settings(SUBURB_MERGE_MEL_GC=True)
    def test_mel_gc_transfer_redirects_to_shuttle(self):
        r = self.get('/melbourne/airport-transfer/werribee/')
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], '/melbourne/airport-shuttle/werribee/')
        page = self.get('/melbourne/airport-shuttle/werribee/')
        self.assertContains(page, 'Werribee Airport Shuttle &amp; Transfer Melbourne | EasyGo')
        self.assertContains(page, 'href="https://easygoshuttle.com.au/melbourne/airport-shuttle/werribee/"')
        # Sydney 는 이 스위치와 무관
        self.assertEqual(self.get('/sydney/airport-transfer/penrith/').status_code, 200)

    @override_settings(SUBURB_MERGE_SYDNEY_PILOT=True)
    def test_sydney_pilot_only(self):
        r = self.get('/sydney/airport-shuttle/penrith/')        # 시범: transfer 를 남긴다
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], '/sydney/airport-transfer/penrith/')
        r = self.get('/sydney/airport-transfer/box-hill/')      # 시범: shuttle 을 남긴다
        self.assertEqual(r['Location'], '/sydney/airport-shuttle/box-hill/')
        for url in ['/sydney/airport-shuttle/hornsby/', '/sydney/airport-transfer/hornsby/']:  # 비교 그룹
            self.assertEqual(self.get(url).status_code, 200, url)
        self.assertEqual(sitemap_services('sydney', 'penrith'), ('transfer',))
        self.assertEqual(sitemap_services('sydney', 'hornsby'), ('shuttle', 'transfer'))
        html = Template("{% load suburb_links %}{% suburb_url 'sydney' 'penrith' 'shuttle' %}").render(Context())
        self.assertEqual(html, '/sydney/airport-transfer/penrith/')


@patch('blog.bird_proxy.create_bird_mapping', return_value=True)
@patch('blog.bird_proxy.close_bird_mapping', return_value=True)
class SuburbLocalReviewsTests(TestCase):
    def setUp(self):
        from blog.models import Post as Booking
        from easygo_review.models import Post as Review
        cache.clear()
        self.syd = region('sydney', 'Sydney')
        RegionSuburb.objects.get_or_create(region=self.syd, slug='hornsby-heights',
                                           defaults={'name': 'Hornsby Heights', 'price': 100, 'is_active': True})
        d = datetime.date(2026, 11, 1)
        Booking.objects.create(name='Kath Riddell', email='k@x.com', no_of_passenger='1', price='100',
                               suburb='Hornsby Hts', pickup_date=d - datetime.timedelta(days=5))
        Booking.objects.create(name='Other Person', email='o@x.com', no_of_passenger='1', price='100',
                               suburb='Ryde', pickup_date=d - datetime.timedelta(days=5))
        Review.objects.create(name='Kath Riddell', author='Kath Riddell', content='Driver was on time', date=d)
        Review.objects.create(name='Other Person', author='Other Person', content='From Ryde', date=d)

    def get(self, url):
        return self.client.get(url, secure=True)

    def test_off_by_default(self, *_):
        self.assertNotContains(self.get('/sydney/airport-shuttle/hornsby-heights/'), 'customers say')

    @override_settings(SUBURB_LOCAL_REVIEWS=True)
    def test_shows_only_this_suburbs_reviews_on_one_page(self, *_):
        page = self.get('/sydney/airport-shuttle/hornsby-heights/')
        self.assertContains(page, 'What Hornsby Heights customers say')
        self.assertContains(page, 'Driver was on time')
        self.assertContains(page, 'Kath Riddell, Hornsby Heights')
        self.assertNotContains(page, 'From Ryde')
        # 합쳐지지 않은 서버브는 shuttle 페이지에만 — transfer 에 같은 후기를 반복하지 않는다.
        self.assertNotContains(self.get('/sydney/airport-transfer/hornsby-heights/'), 'customers say')
