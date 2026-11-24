import datetime
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from blog.models import Inquiry, Post


@override_settings(RATELIMIT_ENABLE=False)
class EmailDispatchAddressLookupTests(TestCase):
    """Email dispatch finds bookings by any of email / booker_email / email1 (2026-11-24).
    Before, most options only matched `email`, so entering the booker's address did nothing."""

    def setUp(self):
        self.client.force_login(User.objects.create_user('staff', 'staff@example.com', 'pw'))
        self.today = timezone.localdate()
        patches = [
            mock.patch('basecamp.views.admin_ops.handle_email_sending'),
            mock.patch('basecamp.views.admin_ops.send_sms_notice'),
            mock.patch('basecamp.views.admin_ops.send_telegram_task'),
        ]
        self.mocks = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)
        self.send_email = self.mocks[0]

    def _post(self, **kw):
        defaults = dict(name='Pax', email='pax@example.com', price='100', paid='0',
                        pickup_date=self.today + datetime.timedelta(days=3), pickup_time='10:00')
        defaults.update(kw)
        return Post.objects.create(**defaults)

    def _dispatch(self, address, option, **extra):
        data = {'email': address, 'selected_option': option, 'phone_verify': ''}
        data.update(extra)
        return self.client.post('/email_dispatch_detail/', data, secure=True)

    def test_payment_reminder_by_booker_email(self):
        self._post(booker_email='boss@company.com')
        r = self._dispatch('boss@company.com', 'Payment Reminder')
        self.assertNotEqual(r.status_code, 400)
        ctx = self.send_email.call_args.args[4]
        self.assertEqual(len(ctx['unpaid_bookings']), 1)

    def test_payment_reminder_by_email1(self):
        self._post(email1='other@family.com')
        self._dispatch('OTHER@family.com', 'Payment Reminder')
        self.assertEqual(len(self.send_email.call_args.args[4]['unpaid_bookings']), 1)

    def test_gratitude_applies_payment_to_booking_found_by_booker_email(self):
        b = self._post(booker_email='boss@company.com', price='120')
        self._dispatch('boss@company.com', 'Gratitude For Payment', payment_amount='120')
        b.refresh_from_db()
        self.assertEqual(float(b.paid), 120.0)

    def test_adjusted_pickup_time_by_booker_email(self):
        b = self._post(booker_email='boss@company.com')
        self._dispatch('boss@company.com', 'Adjusted Pickup Time', adjusted_pickup_time='08:15')
        b.refresh_from_db()
        self.assertEqual(b.pickup_time, '08:15')

    def test_round_trip_cancel_hits_the_sibling_not_another_booking(self):
        out_date = self.today + datetime.timedelta(days=3)
        back_date = self.today + datetime.timedelta(days=10)
        # an unrelated booking by the same booker
        other = self._post(email='someone@else.com', booker_email='boss@company.com',
                           pickup_date=self.today + datetime.timedelta(days=20))
        outbound = self._post(booker_email='boss@company.com', pickup_date=out_date, return_pickup_date=back_date)
        ret = self._post(booker_email='boss@company.com', pickup_date=back_date, return_pickup_date=out_date,
                         return_pickup_time='x')
        self._dispatch('boss@company.com', 'Cancellation by Client')
        for b in (other, outbound, ret):
            b.refresh_from_db()
        self.assertTrue(ret.cancelled)
        self.assertTrue(outbound.cancelled)
        self.assertFalse(other.cancelled)

    def test_inquiry_found_by_booker_email(self):
        Inquiry.objects.create(name='Pax', email='pax@example.com', booker_email='boss@company.com',
                               pickup_date=self.today + datetime.timedelta(days=5))
        r = self._dispatch('boss@company.com', 'Payment Method')
        self.assertNotIn(b'User not found', r.content)
        self.assertTrue(self.send_email.called)
