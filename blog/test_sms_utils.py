"""전화번호 정규화 (blog/sms_utils.normalize_phone)."""

from django.test import SimpleTestCase

from blog.sms_utils import normalize_phone


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
