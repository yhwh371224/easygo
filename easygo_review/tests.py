"""Tests for the easygo_review app.

지금은 search-survey(구글에서 EasyGo 를 찾아보고 첫인상을 남기는 설문) 쪽만 있다.
blog 에서 옮겨온 것이라 히스토리는 blog/tests.py 에 있었다.
"""
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from easygo_review.models import SearchSurveyResponse


# ---------------------------------------------------------------------------
# Search survey — 제출 동작 + (보류 중인) 할인 코드 기능
# ---------------------------------------------------------------------------

@override_settings(TURNSTILE_DISABLED=True, SURVEY_DISCOUNT_AMOUNT=10,
                   SURVEY_DISCOUNT_VALID_DAYS=90, RATELIMIT_ENABLE=False)
class SearchSurveySubmitTests(TestCase):
    """설문 제출 자체. 할인 코드 자동 발급은 2026-09-16 에 보류했으므로
    제출만으로는 코드도 안 나가고 참여자에게 메일도 가지 않아야 한다 —
    페이지에서 약속하지 않은 걸 조용히 주고 있으면 그게 버그다."""

    def setUp(self):
        self.client = Client()
        self.url = reverse('search_survey')
        self.payload = {
            'name': 'Jane Tester',
            'email': 'jane@example.com',
            'keyword': 'sydney airport shuttle',
            'page': 'Page 1',
            'landed': 'Yes, the homepage loaded straight away',
            'landed_note': '',
            'liked': 'clean',
            'improve': 'nothing',
        }

    def _post(self):
        with patch('easygo_review.search_survey_views.send_telegram_sync'):
            return self.client.post(self.url, self.payload)

    def test_submission_is_saved(self):
        response = self._post()
        self.assertTrue(response.context['submitted'])
        entry = SearchSurveyResponse.objects.get(email='jane@example.com')
        self.assertEqual(entry.keyword, 'sydney airport shuttle')
        self.assertEqual(entry.page, 'Page 1')

    def test_no_discount_code_is_issued_or_emailed(self):
        response = self._post()

        entry = SearchSurveyResponse.objects.get(email='jane@example.com')
        self.assertIsNone(entry.discount_code)
        self.assertIsNone(entry.discount_emailed)

        self.assertFalse([m for m in mail.outbox if 'jane@example.com' in m.to])
        self.assertNotContains(response, 'discount')

    def test_admin_notification_omits_the_code_line(self):
        self._post()
        internal = [m for m in mail.outbox if 'jane@example.com' not in m.to]
        self.assertTrue(internal)
        self.assertNotIn('Discount code issued', internal[0].body)

    def test_invalid_submission_is_not_saved(self):
        self.payload['page'] = 'Page 99'
        response = self._post()
        self.assertFalse(response.context['submitted'])
        self.assertFalse(SearchSurveyResponse.objects.exists())


@override_settings(SURVEY_DISCOUNT_AMOUNT=10, SURVEY_DISCOUNT_VALID_DAYS=90)
class SearchSurveyDiscountMachineryTests(TestCase):
    """할인 코드 발급/발송 자체는 살려뒀다 — admin 의 수동 재발송 액션이 쓰고,
    나중에 자동 발급을 되살릴 때 바로 돌아야 한다. 그때까지 썩지 않게 직접 검증."""

    def _entry(self, email='jane@example.com'):
        return SearchSurveyResponse.objects.create(
            name='Jane Tester', email=email, keyword='k',
            page='Page 1', landed='Yes, the homepage loaded straight away',
        )

    def test_issue_discount_code_sets_amount_and_expiry(self):
        entry = self._entry()
        code = entry.issue_discount_code()

        self.assertTrue(code.startswith('EG-'))
        self.assertEqual(entry.discount_amount, 10)
        self.assertEqual(entry.discount_expires,
                         timezone.localdate() + timedelta(days=90))
        self.assertTrue(entry.discount_is_valid)

    def test_issuing_twice_keeps_the_first_code(self):
        entry = self._entry()
        first = entry.issue_discount_code()
        self.assertEqual(entry.issue_discount_code(), first)

    def test_codes_are_unique(self):
        codes = {self._entry(f'p{i}@example.com').issue_discount_code()
                 for i in range(25)}
        self.assertEqual(len(codes), 25)

    def test_send_discount_code_emails_the_participant(self):
        from easygo_review.search_survey_views import _send_discount_code

        entry = self._entry()
        entry.issue_discount_code()
        _send_discount_code(entry)

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['jane@example.com'])
        self.assertIn(entry.discount_code, sent.subject)
        body = sent.alternatives[0][0]
        self.assertIn(entry.discount_code, body)
        self.assertIn('$10', body)

        entry.refresh_from_db()
        self.assertIsNotNone(entry.discount_emailed)

    def test_redeemed_code_is_no_longer_valid(self):
        entry = self._entry()
        entry.issue_discount_code()
        entry.discount_redeemed = timezone.now()
        entry.save(update_fields=['discount_redeemed'])
        self.assertFalse(entry.discount_is_valid)
