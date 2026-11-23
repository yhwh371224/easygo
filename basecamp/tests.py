from django.test import TestCase

from regions.models import Region, RegionSuburb


class MaxiTaxiSuburbRedirectTests(TestCase):
    """2026-11-24: /maxi-taxi/<suburb>/ pages kept only for the 6 suburbs linked from
    /maxi-taxi/; every other old URL 301s straight to /maxi-taxi/ (no chains)."""

    def setUp(self):
        region = Region.objects.create(slug='sydney', name='Sydney', timezone='Australia/Sydney',
                                       phone='0200000000', is_active=True)
        for slug, name in [('chatswood', 'Chatswood'), ('hotels-in-cbd', 'Hotels In CBD'), ('penrith', 'Penrith')]:
            RegionSuburb.objects.create(region=region, name=name, slug=slug, price=100, zone='north_shore')

    def assertRedirect301(self, url, target):
        r = self.client.get(url, secure=True)
        self.assertEqual(r.status_code, 301, url)
        self.assertEqual(r['Location'], target)

    def test_kept_suburb_page_renders(self):
        r = self.client.get('/maxi-taxi/chatswood/', secure=True)
        self.assertEqual(r.status_code, 200)

    def test_other_suburb_redirects_to_pillar(self):
        self.assertRedirect301('/maxi-taxi/penrith/', '/maxi-taxi/')

    def test_uppercase_kept_suburb_redirects_to_lowercase(self):
        self.assertRedirect301('/maxi-taxi/Chatswood/', '/maxi-taxi/chatswood/')

    def test_old_hotels_in_city_link_goes_to_hotels_in_cbd(self):
        self.assertRedirect301('/maxi-taxi/hotels-in-city/', '/maxi-taxi/hotels-in-cbd/')

    def test_legacy_underscore_urls_redirect_in_one_hop(self):
        self.assertRedirect301('/maxi_taxi/penrith/', '/maxi-taxi/')
        self.assertRedirect301('/maxi_taxi/chatswood/', '/maxi-taxi/chatswood/')

    def test_more_suburbs_list_redirects_to_pillar(self):
        self.assertRedirect301('/more_suburbs_maxi_taxi/', '/maxi-taxi/')

    def test_pillar_links_only_the_six_kept_suburbs(self):
        r = self.client.get('/maxi-taxi/', secure=True)
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('/maxi-taxi/chatswood/', html)
        self.assertIn('/maxi-taxi/hotels-in-cbd/', html)
        self.assertNotIn('/maxi-taxi/hotels-in-city/', html)
        self.assertNotIn('/more_suburbs_maxi_taxi/', html)
        self.assertNotIn('Search your Sydney suburb', html)
        self.assertNotIn('수버브별', html)  # 템플릿 주석이 화면에 새지 않게

    def test_kept_suburb_page_is_indexable_with_one_canonical(self):
        html = self.client.get('/maxi-taxi/chatswood/', secure=True).content.decode()
        self.assertNotIn('noindex', html)
        self.assertEqual(html.count('rel="canonical"'), 1)
