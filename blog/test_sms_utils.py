"""전화번호 정규화 (blog/sms_utils.normalize_phone) + SMS 성공 텔레그램 알림."""

import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from blog.sms_utils import normalize_phone, send_sms_notice, sms_sent_alert_text


class SmsSentAlertTests(SimpleTestCase):
    booking = SimpleNamespace(name='Leo Tang', email='leo@example.com',
                              pickup_date=datetime.date(2026, 11, 30), pickup_time='07:15')

    def test_alert_text_shows_who_email_and_date(self):
        text = sms_sent_alert_text('+6596908362', self.booking, 'manual')
        self.assertIn('SMS sent — manual', text)
        self.assertIn('To: Leo Tang (+6596908362)', text)
        self.assertIn('Email: leo@example.com', text)
        self.assertIn('Pickup: 2026-11-30 07:15', text)

    @patch('blog.tasks.send_telegram_task.delay')
    @patch('blog.sms_utils.get_client')
    def test_success_sends_telegram_failure_does_not(self, client, telegram):
        client.return_value.messages.create.return_value = MagicMock(sid='SM1')
        self.assertEqual(send_sms_notice('006596908362', 'hi', booking=self.booking), 'SM1')
        telegram.assert_called_once()
        self.assertIn('Leo Tang', telegram.call_args.args[0])
        telegram.reset_mock()
        self.assertIsNone(send_sms_notice('12345', 'hi', booking=self.booking))   # 잘못된 번호
        telegram.assert_not_called()
        send_sms_notice('0412 345 678', 'hi', notify=False)                       # 기사 알림 등
        telegram.assert_not_called()


class NormalizePhoneTests(SimpleTestCase):
    def test_international_00_prefix(self):
        self.assertEqual(normalize_phone('006596908362'), '+6596908362')      # 싱가포르
        self.assertEqual(normalize_phone('0064 21 123 4567'), '+64211234567')  # 뉴질랜드

    def test_australian_0011_prefix(self):
        self.assertEqual(normalize_phone('0011 65 9690 8362'), '+6596908362')

    def test_single_zero_or_no_prefix_before_country_code(self):
        self.assertEqual(normalize_phone('065 9690 8362'), '+6596908362')      # 0 하나 + 싱가포르
        self.assertEqual(normalize_phone('6596908362'), '+6596908362')         # 국가번호만
        self.assertEqual(normalize_phone('064 21 123 4567'), '+64211234567')   # 0 하나 + 뉴질랜드
        self.assertEqual(normalize_phone('821012345678'), '+821012345678')     # 한국
        self.assertEqual(normalize_phone('1-917-833-4736'), '+19178334736')    # 미국
        self.assertIsNone(normalize_phone('9512853388'))                        # 미국 1 빠짐 ≠ 미얀마 유선

    def test_existing_forms_unchanged(self):
        self.assertEqual(normalize_phone('0412 345 678'), '+61412345678')
        self.assertEqual(normalize_phone('02 9123 4567'), '+61291234567')      # 호주 유선
        self.assertEqual(normalize_phone('412 345 678'), '+61412345678')
        self.assertEqual(normalize_phone('+61 412 345 678'), '+61412345678')
        self.assertEqual(normalize_phone('+65 9690 8362'), '+6596908362')
        self.assertIsNone(normalize_phone('12345'))
        self.assertIsNone(normalize_phone(''))
