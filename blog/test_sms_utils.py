"""전화번호 정규화 (blog/sms_utils.normalize_phone)."""

from django.test import SimpleTestCase

from blog.sms_utils import normalize_phone


class NormalizePhoneTests(SimpleTestCase):
    def test_international_00_prefix(self):
        self.assertEqual(normalize_phone('006596908362'), '+6596908362')      # 싱가포르
        self.assertEqual(normalize_phone('0064 21 123 4567'), '+64211234567')  # 뉴질랜드

    def test_australian_0011_prefix(self):
        self.assertEqual(normalize_phone('0011 65 9690 8362'), '+6596908362')

    def test_existing_forms_unchanged(self):
        self.assertEqual(normalize_phone('0412 345 678'), '+61412345678')
        self.assertEqual(normalize_phone('+61 412 345 678'), '+61412345678')
        self.assertEqual(normalize_phone('+65 9690 8362'), '+6596908362')
        self.assertIsNone(normalize_phone('12345'))
        self.assertIsNone(normalize_phone(''))
