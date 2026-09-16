from django.test import TestCase, Client, override_settings
from django.urls import reverse
from regions.models import Region


@override_settings(RATELIMIT_ENABLE=False)
class SurveyBannerTests(TestCase):
    """홈 5종 전부에 설문 배너가 떠야 한다. 할인 약속은 2026-09-16 에 뺐으므로
    배너가 다시 할인을 약속하기 시작하면 잡아낸다."""

    @classmethod
    def setUpTestData(cls):
        for slug, name in [('sydney', 'Sydney'), ('brisbane', 'Brisbane'),
                           ('melbourne', 'Melbourne'), ('gold-coast', 'Gold Coast'),
                           ('perth', 'Perth')]:
            Region.objects.create(slug=slug, name=name, is_active=True)

    def _assert_banner(self, url):
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200, url)
        self.assertContains(r, 'survey-banner', msg_prefix=url)
        self.assertContains(r, 'href="/search-survey/"', msg_prefix=url)
        self.assertNotContains(r, 'off your next booking', msg_prefix=url)

    def test_sydney(self):
        self._assert_banner('/')

    def test_generic_region(self):
        self._assert_banner('/perth/')

    def test_city_pages(self):
        for url in ['/brisbane/', '/melbourne/', '/gold-coast/']:
            self._assert_banner(url)
