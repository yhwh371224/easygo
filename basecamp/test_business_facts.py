"""회사 사실 정보 — schema, About 숫자, /llms.txt (basecamp/business_facts.py)."""

import datetime
import json
import re
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from basecamp import business_facts
from basecamp.business_facts import rounded_down, stats


def ld_blocks(html):
    return [json.loads(b) for b in re.findall(r'<script[^>]*ld\+json[^>]*>(.*?)</script>', html, re.S)]


@patch('blog.bird_proxy.create_bird_mapping', return_value=True)
@patch('blog.bird_proxy.close_bird_mapping', return_value=True)
class BusinessFactsTests(TestCase):
    def setUp(self):
        from blog.models import Post
        cache.clear()
        past = datetime.date.today() - datetime.timedelta(days=10)
        for i, (email, pax) in enumerate([('a@x.com', '6'), ('a@x.com', '2'), ('b@x.com', '3')]):
            Post.objects.create(name=f'P{i}', email=email, no_of_passenger=pax, price='100', pickup_date=past)
        Post.objects.create(name='Cancelled', email='c@x.com', no_of_passenger='9', price='100',
                            pickup_date=past, cancelled=True)

    def test_stats_from_bookings(self, *_):
        n = stats()
        self.assertEqual(n['trips'], 3)
        self.assertEqual(n['customers'], 2)
        self.assertEqual(n['repeat_pct'], 50)
        self.assertEqual(n['group_pct'], 33)

    def test_rounded_down(self, *_):
        self.assertEqual(rounded_down(5323), '5,300+')
        self.assertEqual(rounded_down(42), '42')

    def test_about_page_shows_numbers(self, *_):
        r = self.client.get('/about_us/', secure=True)
        self.assertContains(r, 'EasyGo in numbers')
        self.assertContains(r, '50%')
        self.assertNotContains(r, 'completed trips')
        self.assertContains(r, 'started in Sydney in 2014')
        self.assertNotContains(r, 'owner')

    def test_about_page_has_the_company_details(self, *_):
        r = self.client.get('/about_us/', secure=True)
        for text in ('ABN: 25 697 358 535', 'Our history', 'under new management', '50 minutes', '33%',
                     'id="company-information"'):
            self.assertContains(r, text)
        self.assertNotContains(r, 'href="/company/"')
        self.assertContains(self.client.get('/', secure=True), 'href="/about_us/">About us')   # 푸터 링크

    def test_old_company_page_redirects_to_about(self, *_):
        r = self.client.get('/company/', secure=True)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], '/about_us/#company-information')

    @patch.object(business_facts, 'FOUNDED_YEAR', None)
    @patch.object(business_facts, 'ABN', '')
    def test_unconfirmed_facts_hidden(self, *_):
        r = self.client.get('/about_us/', secure=True)
        self.assertNotContains(r, 'Our history')
        self.assertNotContains(r, 'ABN')

    def test_llms_txt(self, *_):
        r = self.client.get('/llms.txt', secure=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('text/plain'))
        self.assertIn('# EasyGo Airport Shuttle', r.content.decode())
        self.assertIn('50% of customers have booked more than once', r.content.decode())
        self.assertNotIn('Completed trips', r.content.decode())
        self.assertIn('Founded in 2014', r.content.decode())
        self.assertNotIn('/company/', r.content.decode())

    def test_home_schema_is_valid_json_with_same_as_and_real_geo(self, *_):
        r = self.client.get('/', secure=True)
        business = [b for b in ld_blocks(r.content.decode()) if b.get('@type') == 'LocalBusiness']
        self.assertTrue(business)
        for b in business:
            self.assertIn('sameAs', b)
        home = [b for b in business if 'geo' in b][0]
        self.assertEqual(home['geo']['latitude'], business_facts.LATITUDE)
        self.assertEqual(home['openingHours'], 'Mo-Su 00:00-23:59')

    @patch.object(business_facts, 'FOUNDED_YEAR', 2019)
    @patch.object(business_facts, 'P2P_AUTHORISATION', 'BSP-123')
    def test_optional_facts_appear_once_filled(self, *_):
        r = self.client.get('/about_us/', secure=True)
        self.assertContains(r, '<strong>2019</strong> — EasyGo Airport Shuttle started')
        self.assertContains(r, 'BSP-123')
        for b in ld_blocks(r.content.decode()):
            if b.get('@type') == 'LocalBusiness':
                self.assertEqual(b['foundingDate'], '2019')
                self.assertEqual(b['hasCredential']['identifier'], 'BSP-123')
