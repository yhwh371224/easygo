import datetime
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from blog.models import Inquiry, Post


@override_settings(RATELIMIT_ENABLE=False)
class ConfirmBookingAddressTests(TestCase):
    """confirm_booking: find the inquiry by booker_email / email / email1, and keep the
    passenger's own email on the booking even when the booker's address was typed in."""

    def setUp(self):
        patches = [
            mock.patch('basecamp.views.bookings.send_telegram_task'),
            mock.patch('basecamp.views.bookings.send_post_confirmation_email_task'),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.day = (timezone.localdate() + datetime.timedelta(days=10)).isoformat()

    def _inquiry(self, **kw):
        defaults = dict(name='Pax', email='pax@example.com', pickup_date=self.day, pickup_time='10:00',
                        direction='Drop off to Domestic Airport', suburb='Hornsby', price='120')
        defaults.update(kw)
        return Inquiry.objects.create(**defaults)

    def _confirm(self, address, url='/confirm_booking_detail/'):
        return self.client.post(url, {'email': address, 'index': '1', 'is_confirmed': 'True'}, secure=True)

    def test_booker_email_keeps_passenger_email_on_booking(self):
        self._inquiry(booker_email='boss@company.com')
        self._confirm('boss@company.com')
        post = Post.objects.get()
        self.assertEqual(post.email, 'pax@example.com')
        self.assertEqual(post.booker_email, 'boss@company.com')

    def test_email1_finds_the_inquiry(self):
        self._inquiry(email1='partner@family.com')
        self._confirm('Partner@Family.com')
        self.assertEqual(Post.objects.get().email, 'pax@example.com')

    def test_prepay_path_also_keeps_passenger_email(self):
        self._inquiry(booker_email='boss@company.com')
        self._confirm('boss@company.com', url='/confirm_booking_prepay_detail/')
        self.assertEqual(Post.objects.get().email, 'pax@example.com')

    def test_returning_booker_is_not_treated_as_first_time(self):
        # 이전 예약이 있는 예약자 — 도착편이어도 첫 이용 선결제 강제가 걸리면 안 된다
        Post.objects.create(name='Old', email='someone@else.com', booker_email='boss@company.com',
                            price='100', pickup_date=timezone.localdate() - datetime.timedelta(days=30),
                            cancelled=False, pending=False, cash=True)
        self._inquiry(booker_email='boss@company.com', direction='Pickup from Domestic Airport')
        self.client.post('/confirm_booking_detail/', {'email': 'boss@company.com', 'index': '1',
                                                      'is_confirmed': 'True', 'cash': 'on'}, secure=True)
        new = Post.objects.exclude(name='Old').get()
        self.assertFalse(new.prepay)
