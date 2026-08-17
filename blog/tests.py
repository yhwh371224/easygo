"""
Tests for the blog app: models, driver views, and business logic.

Celery tasks use transaction.on_commit which never fires inside TestCase
(the DB transaction is never committed), so email/calendar tasks are safe.
Bird proxy calls are patched where they would run synchronously.
"""
import base64
import datetime
import hashlib
import hmac
import json
import time
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch, MagicMock

import pytz
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from utils.command_alerts import TelegramAlertMixin
from blog.models import (
    VirtualNumber, Driver, DriverSettlement,
    Inquiry, Post, PaypalPayment, StripePayment, PhoneMapping,
)
from blog.models.driver import DriverSettlementItem
from blog.sms_utils import format_au_phone
from regions.models import Region


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_region(slug='test-region', name='Test Region'):
    return Region.objects.create(
        slug=slug,
        name=name,
        timezone='Australia/Sydney',
        phone='0200000000',
    )


def make_user(username='testdriver', password='Pass1234!'):
    return User.objects.create_user(username=username, password=password)


def make_driver(user=None, region=None, must_change_password=False):
    if user is None:
        user = make_user()
    return Driver.objects.create(
        user=user,
        driver_name='Test Driver',
        driver_contact='0400000000',
        driver_email='driver@example.com',
        must_change_password=must_change_password,
        region=region,
    )


FUTURE_DATE = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()


# ---------------------------------------------------------------------------
# Model: VirtualNumber
# ---------------------------------------------------------------------------

class VirtualNumberModelTests(TestCase):

    def test_str_flags_a_number_bird_does_not_route(self):
        """The admin picks numbers off this label; an unwired one reaches nobody."""
        vn = VirtualNumber.objects.create(number='+61200000001')
        self.assertEqual(str(vn), '+61200000001 (not wired)')
        self.assertFalse(vn.is_wired)

    def test_str_is_bare_once_wired(self):
        vn = VirtualNumber.objects.create(
            number='+61200000004',
            sms_channel_id='sms-channel',
            voice_channel_id='voice-channel',
        )
        self.assertEqual(str(vn), '+61200000004')
        self.assertTrue(vn.is_wired)

    def test_one_channel_alone_is_not_wired(self):
        vn = VirtualNumber.objects.create(
            number='+61200000005', voice_channel_id='voice-only',
        )
        self.assertFalse(vn.is_wired)

    def test_number_unique(self):
        VirtualNumber.objects.create(number='+61200000002')
        with self.assertRaises(Exception):
            VirtualNumber.objects.create(number='+61200000002')


# ---------------------------------------------------------------------------
# Model: Driver
# ---------------------------------------------------------------------------

class DriverModelTests(TestCase):

    def test_create_driver(self):
        driver = make_driver()
        self.assertEqual(driver.driver_name, 'Test Driver')
        self.assertFalse(driver.must_change_password)

    def test_str_returns_driver_name(self):
        driver = make_driver()
        self.assertEqual(str(driver), 'Test Driver')

    def test_driver_with_virtual_number(self):
        vn = VirtualNumber.objects.create(number='+61200000003')
        driver = make_driver()
        driver.virtual_number = vn
        driver.save()
        self.assertEqual(driver.virtual_number.number, '+61200000003')

    def test_driver_region_nullable(self):
        driver = make_driver()
        self.assertIsNone(driver.region)

    def test_driver_is_default_false_by_default(self):
        driver = make_driver()
        self.assertFalse(driver.is_default)


# ---------------------------------------------------------------------------
# Model: DriverSettlement
# ---------------------------------------------------------------------------

class DriverSettlementModelTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@x.com', 'pass')
        self.driver = make_driver()

    def test_create_settlement(self):
        s = DriverSettlement.objects.create(
            driver=self.driver,
            amount=Decimal('150.00'),
            note='Weekly run',
            settled_by=self.admin,
        )
        self.assertEqual(s.amount, Decimal('150.00'))

    def test_str_contains_driver_and_amount(self):
        s = DriverSettlement.objects.create(
            driver=self.driver,
            amount=Decimal('75.50'),
            settled_by=self.admin,
        )
        self.assertIn('Test Driver', str(s))
        self.assertIn('75.50', str(s))

    def test_ordering_newest_first(self):
        s1 = DriverSettlement.objects.create(driver=self.driver, amount=Decimal('10'), settled_by=self.admin)
        s2 = DriverSettlement.objects.create(driver=self.driver, amount=Decimal('20'), settled_by=self.admin)
        qs = list(DriverSettlement.objects.filter(driver=self.driver))
        self.assertEqual(qs[0].pk, s2.pk)

    def test_cascade_delete_with_driver(self):
        DriverSettlement.objects.create(driver=self.driver, amount=Decimal('50'), settled_by=self.admin)
        driver_pk = self.driver.pk
        self.driver.delete()
        self.assertFalse(DriverSettlement.objects.filter(driver_id=driver_pk).exists())


# ---------------------------------------------------------------------------
# Model: Inquiry
# ---------------------------------------------------------------------------

class InquiryModelTests(TestCase):

    def setUp(self):
        self.region = make_region()

    def test_create_minimal_inquiry(self):
        inq = Inquiry.objects.create(
            name='Alice',
            email='alice@example.com',
            no_of_passenger='2',
        )
        self.assertEqual(inq.name, 'Alice')
        self.assertFalse(inq.is_confirmed)
        self.assertFalse(inq.cancelled)
        self.assertFalse(inq.sent_email)

    def test_inquiry_defaults(self):
        inq = Inquiry.objects.create(name='Bob', email='bob@example.com', no_of_passenger='1')
        self.assertFalse(inq.cash)
        self.assertFalse(inq.cruise)
        self.assertFalse(inq.prepay)
        self.assertFalse(inq.pending)

    def test_inquiry_with_region(self):
        inq = Inquiry.objects.create(
            name='Carol',
            email='carol@example.com',
            no_of_passenger='3',
            region=self.region,
        )
        self.assertEqual(inq.region.slug, 'test-region')

    def test_ordering_newest_first(self):
        i1 = Inquiry.objects.create(name='X', email='x@x.com', no_of_passenger='1')
        i2 = Inquiry.objects.create(name='Y', email='y@y.com', no_of_passenger='1')
        qs = list(Inquiry.objects.all())
        self.assertEqual(qs[0].pk, i2.pk)


# ---------------------------------------------------------------------------
# Model: Post
# ---------------------------------------------------------------------------

class PostModelTests(TestCase):

    def setUp(self):
        self.region = make_region()

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_create_minimal_post(self, mock_close, mock_create):
        post = Post.objects.create(
            name='Dan',
            email='dan@example.com',
            no_of_passenger='2',
            price='100',
        )
        self.assertEqual(post.name, 'Dan')
        self.assertFalse(post.cancelled)

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_invoice_name_uses_booker_name_when_set(self, mock_close, mock_create):
        post = Post.objects.create(
            name='Eve',
            booker_name='Corp Booker',
            email='eve@example.com',
            no_of_passenger='1',
            price='80',
        )
        self.assertEqual(post.invoice_name, 'Corp Booker')

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_invoice_name_falls_back_to_name(self, mock_close, mock_create):
        post = Post.objects.create(
            name='Frank',
            email='frank@example.com',
            no_of_passenger='1',
            price='60',
        )
        self.assertEqual(post.invoice_name, 'Frank')

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_ordering_newest_first(self, mock_close, mock_create):
        p1 = Post.objects.create(name='G', email='g@g.com', no_of_passenger='1', price='10')
        p2 = Post.objects.create(name='H', email='h@h.com', no_of_passenger='1', price='10')
        qs = list(Post.objects.all())
        self.assertEqual(qs[0].pk, p2.pk)

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_post_with_region(self, mock_close, mock_create):
        post = Post.objects.create(
            name='Ida',
            email='ida@example.com',
            no_of_passenger='2',
            price='120',
            region=self.region,
        )
        self.assertEqual(post.region.slug, 'test-region')


# ---------------------------------------------------------------------------
# Post.commission_rate autofill
# ---------------------------------------------------------------------------

@patch('blog.bird_proxy.create_bird_mapping', return_value=True)
@patch('blog.bird_proxy.close_bird_mapping', return_value=True)
class PostCommissionRateTests(TestCase):
    """The driver's default rate must be stamped on the booking however the
    driver got assigned, not only through the admin form.

    It was admin-only until 2026-08-17, so every job a driver accepted from
    their own dashboard (driver_accept_job, live 2026-08-09) was booked at 0%
    and settled at the full driver_price — Loly was paid 5% too much on every
    job from 2026-08-11 on.
    """

    def setUp(self):
        self.driver = make_driver()
        self.driver.commission_rate = Decimal('5.00')
        self.driver.save()

    def _post(self, **kw):
        return Post.objects.create(
            name='Pax', email='p@x.com', no_of_passenger='1', price='110',
            driver_price='100', **kw,
        )

    def test_rate_stamped_when_driver_assigned_on_create(self, *_):
        post = self._post(driver=self.driver)
        self.assertEqual(post.commission_rate, Decimal('5.00'))
        self.assertEqual(post.commission_amount, Decimal('5.00'))
        self.assertEqual(post.subcontractor_payout, Decimal('95.00'))

    def test_rate_stamped_when_driver_assigned_later(self, *_):
        post = self._post()
        self.assertEqual(post.commission_rate, Decimal('0'))
        post.driver = self.driver
        post.save()
        self.assertEqual(post.commission_rate, Decimal('5.00'))

    def test_rate_stamped_on_partial_save(self, *_):
        """driver_accept_job saves update_fields=['driver', 'use_proxy'] — the
        rate is worthless if it never reaches the database."""
        post = self._post()
        post.driver = self.driver
        post.use_proxy = True
        post.save(update_fields=['driver', 'use_proxy'])

        post.refresh_from_db()
        self.assertEqual(post.commission_rate, Decimal('5.00'))

    def test_hand_typed_rate_is_not_overwritten(self, *_):
        post = self._post(driver=self.driver, commission_rate=Decimal('12.00'))
        post.save()
        self.assertEqual(post.commission_rate, Decimal('12.00'))

    def test_unassigned_post_keeps_zero_rate(self, *_):
        post = self._post()
        self.assertEqual(post.commission_rate, Decimal('0'))
        self.assertEqual(post.commission_amount, Decimal('0'))

    def test_no_commission_on_driver_collected_cash(self, *_):
        """The customer paid the driver directly, so the company never handled
        the money and charges nothing on it. Stamping a rate would only put a
        deduction on the dashboard that no settlement ever collects."""
        post = self._post(driver=self.driver, cash=True)

        self.assertTrue(post.driver_collected_cash)
        self.assertEqual(post.commission_rate, Decimal('0'))
        self.assertEqual(post.commission_amount, Decimal('0'))
        self.assertEqual(post.subcontractor_payout, Decimal('100.00'))


# ---------------------------------------------------------------------------
# Calendar event description
# ---------------------------------------------------------------------------

@patch('blog.bird_proxy.create_bird_mapping', return_value=True)
@patch('blog.bird_proxy.close_bird_mapping', return_value=True)
class CalendarEventDescriptionTests(TestCase):

    def _post(self, **kw):
        kw.setdefault('pickup_date', datetime.date.today())
        kw.setdefault('pickup_time', '09:00')
        return Post.objects.create(
            name='Pax', email='p@x.com', no_of_passenger='1', price='110', **kw,
        )

    def test_driver_price_in_description(self, *_):
        from utils.calendar_sync import build_event_data

        post = self._post(driver_price='100')
        self.assertIn('dp:$100', build_event_data(post)['description'])

    def test_driver_price_omitted_when_blank(self, *_):
        """price is blank too, so Post.save() has nothing to derive it from."""
        from utils.calendar_sync import build_event_data

        post = self._post(price='', driver_price='')
        self.assertNotIn('dp:$', build_event_data(post)['description'])


# ---------------------------------------------------------------------------
# Model: PaypalPayment
# ---------------------------------------------------------------------------

class PaypalPaymentModelTests(TestCase):

    def test_create_paypal_payment(self):
        p = PaypalPayment.objects.create(
            name='Jack',
            email='jack@x.com',
            amount=Decimal('55.00'),
            txn_id='TXN123',
        )
        self.assertFalse(p.is_processed)
        self.assertIsNone(p.processed_at)

    def test_str_pending(self):
        p = PaypalPayment.objects.create(name='Kate', email='k@k.com', amount=Decimal('30'))
        self.assertIn('Pending', str(p))

    def test_str_done(self):
        p = PaypalPayment.objects.create(
            name='Leo', email='l@l.com', amount=Decimal('40'),
            is_processed=True, processed_at=timezone.now()
        )
        self.assertIn('Done', str(p))


# ---------------------------------------------------------------------------
# Model: StripePayment
# ---------------------------------------------------------------------------

class StripePaymentModelTests(TestCase):

    def test_create_stripe_payment(self):
        p = StripePayment.objects.create(
            name='Mia',
            email='mia@x.com',
            amount=Decimal('99.00'),
            payment_intent_id='pi_abc123',
        )
        self.assertFalse(p.is_processed)

    def test_str_pending(self):
        p = StripePayment.objects.create(
            name='Ned', email='n@n.com', amount=Decimal('50'),
            payment_intent_id='pi_xyz'
        )
        self.assertIn('Pending', str(p))

    def test_payment_intent_id_unique(self):
        StripePayment.objects.create(payment_intent_id='pi_dup', amount=Decimal('10'))
        with self.assertRaises(Exception):
            StripePayment.objects.create(payment_intent_id='pi_dup', amount=Decimal('20'))


# ---------------------------------------------------------------------------
# Model: PhoneMapping
# ---------------------------------------------------------------------------

class PhoneMappingModelTests(TestCase):

    def test_create_phone_mapping(self):
        pm = PhoneMapping.objects.create(
            from_number='+61200000010',
            to_number='+61400000010',
            driver_name='Test Driver',
        )
        self.assertEqual(pm.from_number, '+61200000010')


# ---------------------------------------------------------------------------
# Bird proxy
#
# Regression cover for a live incident: the customer's email advertised the
# shared BIRD_NUMBER while the driver's dashboard showed their pooled virtual
# number, so the two sides dialled different numbers. Worse, the pooled number
# had no Bird webhook at all, so the driver's leg reached nothing and said so
# to no one.
#
# The invariants that keep that from recurring:
#   - every surface resolves the number through one function, so the driver and
#     the customer are never told different things;
#   - a number is only ever advertised once Bird actually routes it to us.
# ---------------------------------------------------------------------------

VOICE_CHANNEL = 'aaaaaaaa-0000-4000-8000-000000000001'
SMS_CHANNEL = 'bbbbbbbb-0000-4000-8000-000000000002'


class ProxyNumberTestCase(TestCase):
    """Shared fixture: one driver, one pooled number, one live session."""

    DRIVER_VNUM = '+61485908774'
    CUSTOMER = '+61411111111'
    DRIVER_PHONE = '+61400000001'

    def setUp(self):
        self.vnum = VirtualNumber.objects.create(number=self.DRIVER_VNUM)
        self.driver = make_driver(user=make_user('proxydrv'))
        self.driver.driver_contact = self.DRIVER_PHONE
        self.driver.virtual_number = self.vnum
        self.driver.save()
        # post_save runs create_bird_mapping, which opens the proxy session.
        self.post = Post.objects.create(
            name='Customer', contact=self.CUSTOMER, driver=self.driver,
            pickup_date=datetime.date.today(),
            pickup_time=timezone.localtime().strftime('%H:%M'),
            direction='Pickup from Intl Airport', use_proxy=True,
        )

    def wire(self):
        """What `sync_bird_channels` does once Bird is routing the number."""
        self.vnum.sms_channel_id = SMS_CHANNEL
        self.vnum.voice_channel_id = VOICE_CHANNEL
        self.vnum.save()

    # -- surfaces ----------------------------------------------------------
    def email_number(self):
        from utils.booking_helper import build_reminder_context
        return build_reminder_context(self.post, '10:00 AM', self.driver)['bird_number']

    def calendar_number(self):
        from utils.calendar_sync import _get_contact_display
        return _get_contact_display(self.post)

    def dashboard_number(self):
        client = Client()
        client.force_login(self.driver.user)
        response = client.get(reverse('blog:driver_dashboard'))
        trips = response.context['trips']
        return trips[0]['proxy_number'] if trips else None

    # -- webhooks ----------------------------------------------------------
    def call(self, from_number, channel_id=VOICE_CHANNEL):
        """Drive the voice webhook; return (bridge_url, bridge_payload)."""
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured['url'] = url
            captured['payload'] = json or {}
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status.return_value = None
            return resp

        path = f'/webhook/bird/voice/{channel_id}/' if channel_id else '/webhook/bird/voice/'
        with patch('blog.bird_webhooks.requests.post', side_effect=fake_post):
            Client().post(
                path,
                data=json.dumps({'payload': {
                    'id': 'call-1', 'from': from_number, 'status': 'starting',
                }}),
                content_type='application/json',
            )
        return captured.get('url'), captured.get('payload', {})

    def text(self, from_number, channel_id=SMS_CHANNEL):
        """Drive the SMS webhook; return the channel we replied on."""
        captured = {}

        def fake_send(to_number, body, channel_id=None):
            captured['to'] = to_number
            captured['channel_id'] = channel_id
            return {}

        with patch('blog.bird_webhooks.send_bird_sms', side_effect=fake_send):
            Client().post(
                f'/webhook/bird/sms/{channel_id}/',
                data=json.dumps({'payload': {
                    'sender': {'contact': {'identifierValue': from_number}},
                    'body': {'text': {'text': 'hi'}},
                }}),
                content_type='application/json',
            )
        return captured


class ProxyNumberResolutionTests(ProxyNumberTestCase):

    def test_unwired_number_is_never_advertised(self):
        """A number assigned in the admin but absent from Bird reaches nobody."""
        self.assertFalse(self.vnum.is_wired)
        self.assertEqual(self.calendar_number(), settings.BIRD_NUMBER)
        self.assertEqual(self.dashboard_number(), settings.BIRD_NUMBER)
        self.assertEqual(self.email_number(), format_au_phone(settings.BIRD_NUMBER))

    def test_wired_number_is_used_everywhere(self):
        self.wire()
        self.assertEqual(self.calendar_number(), self.DRIVER_VNUM)
        self.assertEqual(self.dashboard_number(), self.DRIVER_VNUM)
        self.assertEqual(self.email_number(), format_au_phone(self.DRIVER_VNUM))

    def test_driver_and_customer_are_never_told_different_numbers(self):
        """The actual incident: dashboard said one number, email said another."""
        for wired in (False, True):
            with self.subTest(wired=wired):
                if wired:
                    self.wire()
                self.assertEqual(
                    format_au_phone(self.dashboard_number()),
                    self.email_number(),
                )

    def test_driver_without_a_pooled_number_still_gets_a_session(self):
        self.driver.virtual_number = None
        self.driver.save()
        self.assertTrue(PhoneMapping.objects.filter(from_number=self.CUSTOMER).exists())
        self.assertEqual(self.calendar_number(), settings.BIRD_NUMBER)

    def test_overseas_customer_gets_the_real_contact(self):
        """AU proxy numbers aren't reachable from abroad, so don't pretend."""
        self.wire()
        self.post.contact = '+821012345678'
        self.post.save()
        self.assertIsNone(self.email_number())
        self.assertEqual(self.calendar_number(), '+821012345678')

    def test_no_proxy_when_use_proxy_is_off(self):
        self.post.use_proxy = False
        self.post.save()
        self.assertIsNone(self.email_number())
        self.assertEqual(self.calendar_number(), self.CUSTOMER)


DRIVER2_VOICE_CHANNEL = 'cccccccc-0000-4000-8000-000000000003'
DRIVER2_SMS_CHANNEL = 'dddddddd-0000-4000-8000-000000000004'


class SameCustomerConcurrentBookingsTests(ProxyNumberTestCase):
    """A repeat customer with two live bookings must not lose either proxy
    session — and, short of a proxy number, the dashboard falls back to
    showing the customer's real contact (see dashboard.html), so losing the
    mapping isn't just cosmetic, it leaks the customer's number."""

    def _second_booking(self, pickup_time=None, wire=False):
        driver2 = make_driver(user=make_user('proxydrv2'))
        vnum2 = VirtualNumber.objects.create(number='+61485908775')
        driver2.driver_contact = '+61400000002'
        driver2.virtual_number = vnum2
        driver2.save()
        if wire:
            vnum2.voice_channel_id = DRIVER2_VOICE_CHANNEL
            vnum2.sms_channel_id = DRIVER2_SMS_CHANNEL
            vnum2.save()
        post2 = Post.objects.create(
            name='Customer', contact=self.CUSTOMER, driver=driver2,
            pickup_date=datetime.date.today(),
            pickup_time=pickup_time or timezone.localtime().strftime('%H:%M'),
            direction='Pickup from Intl Airport', use_proxy=True,
        )
        return driver2, post2, vnum2

    def test_second_booking_gets_its_own_mapping_not_a_takeover(self):
        _, post2, _ = self._second_booking()
        self.assertEqual(
            PhoneMapping.objects.filter(from_number=self.CUSTOMER).count(), 2,
        )
        self.assertTrue(PhoneMapping.objects.filter(post=self.post).exists())
        self.assertTrue(PhoneMapping.objects.filter(post=post2).exists())

    def test_dashboard_shows_proxy_not_real_number_for_both_drivers(self):
        driver2, _, _ = self._second_booking()

        self.assertIsNotNone(self.dashboard_number())

        client = Client()
        client.force_login(driver2.user)
        response = client.get(reverse('blog:driver_dashboard'))
        trips = response.context['trips']
        self.assertIsNotNone(trips[0]['proxy_number'])
        self.assertNotEqual(trips[0]['proxy_number'], self.CUSTOMER)

    def test_closing_one_booking_leaves_the_others_mapping_alive(self):
        _, post2, _ = self._second_booking()

        self.post.use_proxy = False
        self.post.save()

        self.assertFalse(PhoneMapping.objects.filter(post=self.post).exists())
        self.assertTrue(PhoneMapping.objects.filter(post=post2).exists())

    def _push_first_booking_pickup_far_away(self):
        """Makes booking 1's pickup hours away so the time-proximity fallback
        would always prefer booking 2 (pickup ~now) — an unambiguous baseline
        to prove channel matching, not clock luck, decides the routing."""
        self.post.pickup_time = (
            timezone.localtime() + datetime.timedelta(hours=5)
        ).strftime('%H:%M')
        self.post.save()

    def test_call_on_a_drivers_own_number_wins_over_the_time_heuristic(self):
        self.wire()
        self._push_first_booking_pickup_far_away()
        driver2, post2, vnum2 = self._second_booking(wire=True)

        _, payload = self.call(self.CUSTOMER, channel_id=VOICE_CHANNEL)
        self.assertEqual(payload['to'], self.DRIVER_PHONE)

        _, payload = self.call(self.CUSTOMER, channel_id=DRIVER2_VOICE_CHANNEL)
        self.assertEqual(payload['to'], driver2.driver_contact)

    def test_text_on_a_drivers_own_number_wins_over_the_time_heuristic(self):
        self.wire()
        self._push_first_booking_pickup_far_away()
        driver2, post2, vnum2 = self._second_booking(wire=True)

        captured = self.text(self.CUSTOMER, channel_id=SMS_CHANNEL)
        self.assertEqual(captured['to'], self.DRIVER_PHONE)

        captured = self.text(self.CUSTOMER, channel_id=DRIVER2_SMS_CHANNEL)
        self.assertEqual(captured['to'], driver2.driver_contact)

    def test_shared_channel_still_falls_back_to_the_time_heuristic(self):
        """Neither driver has a wired number, so only caller ID is known —
        the closest-pickup fallback is the best we can do."""
        self._push_first_booking_pickup_far_away()
        driver2, post2, vnum2 = self._second_booking()

        _, payload = self.call(self.CUSTOMER, channel_id=None)
        self.assertEqual(payload['to'], driver2.driver_contact)


class ProxyBridgeTests(ProxyNumberTestCase):

    def test_both_legs_bridge_on_the_channel_the_call_arrived_on(self):
        """A call_id only exists on its own channel; bridging it elsewhere 400s."""
        self.wire()

        url, payload = self.call(self.CUSTOMER)
        self.assertIn(VOICE_CHANNEL, url)
        self.assertEqual(payload['to'], self.DRIVER_PHONE)
        self.assertEqual(payload['from'], self.DRIVER_VNUM)

        url, payload = self.call(self.DRIVER_PHONE)
        self.assertIn(VOICE_CHANNEL, url)
        self.assertEqual(payload['to'], self.CUSTOMER)
        self.assertEqual(payload['from'], self.DRIVER_VNUM)

    def test_shared_channel_bridges_from_the_shared_number(self):
        url, payload = self.call(self.CUSTOMER, channel_id=None)
        self.assertIn(settings.BIRD_VOICE_CHANNEL_ID, url)
        self.assertEqual(payload['from'], settings.BIRD_NUMBER)

    def test_driver_leg_bridges_when_contact_is_not_stored_as_e164(self):
        """Caller ID always arrives as +61...; driver_contact is free text."""
        for stored in ['0400000001', '0400 000 001', '+61 400 000 001']:
            with self.subTest(driver_contact=stored):
                self.driver.driver_contact = stored
                self.driver.save()
                _, payload = self.call(self.DRIVER_PHONE)
                self.assertEqual(payload.get('to'), self.CUSTOMER)

    def test_unknown_caller_is_not_bridged(self):
        self.assertEqual(self.call('+61499999999'), (None, {}))

    def test_sms_is_answered_on_the_channel_it_arrived_on(self):
        self.wire()
        self.assertEqual(
            self.text(self.CUSTOMER),
            {'to': self.DRIVER_PHONE, 'channel_id': SMS_CHANNEL},
        )
        self.assertEqual(
            self.text(self.DRIVER_PHONE),
            {'to': self.CUSTOMER, 'channel_id': SMS_CHANNEL},
        )


class ProxyWindowTests(ProxyNumberTestCase):
    """Full detail (street address + phone number) only opens up the day
    before pickup and on the day itself — see the `in_window` flag in
    driver_views.py and the pickup_date filter in
    bird_webhooks._get_active_mapping(). Before that, the trip is still
    visible (so the driver can plan around it) but shows suburb-only, no
    phone line at all, and a notice instead."""

    def _push_far_future(self):
        self.post.street = '12 Smith St'
        self.post.suburb = 'Bondi'
        self.post.extra_stop_addresses = ['99 Extra Rd, Somewhere']
        self.post.pickup_date = datetime.date.today() + datetime.timedelta(days=5)
        self.post.save()

    def test_far_future_dashboard_shows_suburb_only_and_no_phone_line(self):
        self._push_far_future()

        client = Client()
        client.force_login(self.driver.user)
        response = client.get(reverse('blog:driver_dashboard'))

        self.assertContains(response, 'Bondi')
        self.assertNotContains(response, '12 Smith St')
        self.assertNotContains(response, '99 Extra Rd')
        self.assertContains(response, 'There is an additional stop on the way')
        self.assertContains(response, 'full booking details will only be visible')
        # No phone line at all pre-window — not even a placeholder number,
        # since the real BIRD_NUMBER is live and dialling it could bridge
        # into an unrelated in-window booking.
        self.assertNotContains(response, 'href="tel:')
        self.assertNotContains(response, settings.BIRD_NUMBER)

        trip = response.context['trips'][0]
        self.assertFalse(trip['in_window'])
        self.assertIsNone(trip['proxy_number'])

    def test_far_future_dashboard_shows_admin_curated_extra_stop_area(self):
        self._push_far_future()
        self.post.extra_stop_area = 'Parramatta'
        self.post.save()

        client = Client()
        client.force_login(self.driver.user)
        response = client.get(reverse('blog:driver_dashboard'))

        self.assertContains(response, 'There is an additional stop, Parramatta on the way')
        self.assertNotContains(response, '99 Extra Rd')

    def test_far_future_dashboard_hides_paid_cash_badges_shows_only_price(self):
        self._push_far_future()
        self.post.driver_price = '150'
        self.post.paid = '2026-07-01'
        self.post.cash = True
        self.post.driver_refund_deduction = Decimal('10.00')
        self.post.commission_amount_override = Decimal('5.00')
        self.post.save()

        client = Client()
        client.force_login(self.driver.user)
        response = client.get(reverse('blog:driver_dashboard'))

        self.assertContains(response, '$150')
        self.assertNotContains(response, '<span class="badge-paid">Paid</span>')
        self.assertNotContains(response, '<span class="badge-cash">Cash</span>')
        self.assertNotContains(response, '<span class="badge-refund">')
        self.assertNotContains(response, '<span class="badge-commission">')

    def test_tomorrow_dashboard_shows_paid_cash_badges(self):
        self.post.pickup_date = datetime.date.today() + datetime.timedelta(days=1)
        self.post.driver_price = '150'
        self.post.cash = True
        self.post.save()

        client = Client()
        client.force_login(self.driver.user)
        response = client.get(reverse('blog:driver_dashboard'))

        self.assertContains(response, '<span class="badge-cash">Cash</span>')

    def test_tomorrow_dashboard_shows_full_address_and_live_number(self):
        self.post.street = '12 Smith St'
        self.post.suburb = 'Bondi'
        self.post.pickup_date = datetime.date.today() + datetime.timedelta(days=1)
        self.post.save()

        client = Client()
        client.force_login(self.driver.user)
        response = client.get(reverse('blog:driver_dashboard'))

        self.assertContains(response, '12 Smith St')
        self.assertNotContains(response, 'full booking details will only be visible')

        trip = response.context['trips'][0]
        self.assertTrue(trip['in_window'])

    def test_far_future_call_is_not_bridged(self):
        self.wire()
        self._push_far_future()
        self.assertEqual(self.call(self.CUSTOMER), (None, {}))

    def test_far_future_text_is_not_answered(self):
        self.wire()
        self._push_far_future()
        self.assertEqual(self.text(self.CUSTOMER), {})

    def test_reschedule_into_window_opens_it_without_resaving_use_proxy(self):
        """PhoneMapping.pickup_date is a snapshot taken at mapping-creation
        time; only driver/use_proxy changes retrigger create_bird_mapping
        (see signals.py), so a plain reschedule never refreshes it. Routing
        must key off the booking's live pickup_date, not the stale snapshot,
        or a rescheduled-into-window trip would stay silently unbridgeable."""
        self.wire()
        self._push_far_future()
        self.assertEqual(self.call(self.CUSTOMER), (None, {}))

        self.post.pickup_date = datetime.date.today()
        self.post.save()

        _, payload = self.call(self.CUSTOMER)
        self.assertEqual(payload['to'], self.DRIVER_PHONE)


@override_settings(BIRD_NUMBER='+61485922632')
class SyncBirdChannelsTests(TestCase):
    """This command is the only way a number becomes usable, so any number it
    quietly passes over is a number that can never be advertised."""

    # Bird hands out uuids, and the webhook routes only accept uuids.
    SMS_774 = '11111111-1111-4111-8111-111111111111'
    VOICE_774 = '22222222-2222-4222-8222-222222222222'
    SMS_632 = '33333333-3333-4333-8333-333333333333'
    VOICE_632 = '44444444-4444-4444-8444-444444444444'

    CHANNELS = [
        {'id': SMS_774, 'identifier': '+61485908774', 'platformId': 'sms-messagebird'},
        {'id': VOICE_774, 'identifier': '+61485908774', 'platformId': 'voice-messagebird'},
        {'id': SMS_632, 'identifier': '+61485922632', 'platformId': 'sms-messagebird'},
        {'id': VOICE_632, 'identifier': '+61485922632', 'platformId': 'voice-messagebird'},
    ]

    def _run(self, *args):
        def fake_get(url, **kwargs):
            resp = MagicMock()
            resp.json.return_value = {
                'results': self.CHANNELS if url.endswith('/channels') else []
            }
            resp.raise_for_status.return_value = None
            return resp

        module = 'blog.management.commands.sync_bird_channels.requests'
        with patch(f'{module}.get', side_effect=fake_get), patch(f'{module}.post') as post:
            call_command('sync_bird_channels', *args, stdout=StringIO())
        return post

    def test_shared_company_number_is_wired_like_any_other(self):
        """It was special-cased once, on the theory that settings already knew
        about it. The admin then labelled our busiest number '(not wired)' and
        the resolver warned about it on every single lookup."""
        self._run('--apply')
        shared = VirtualNumber.objects.get(number=settings.BIRD_NUMBER)
        self.assertTrue(shared.is_wired)

    def test_pooled_number_gets_its_channels(self):
        self._run('--apply')
        pooled = VirtualNumber.objects.get(number='+61485908774')
        self.assertEqual(pooled.sms_channel_id, self.SMS_774)
        self.assertEqual(pooled.voice_channel_id, self.VOICE_774)

    def test_subscription_is_registered_per_channel(self):
        """The channel in the URL is the only thing telling the webhook which
        number was dialled, so every channel needs its own subscription."""
        post = self._run('--apply')
        urls = [call.kwargs['json']['url'] for call in post.call_args_list]
        self.assertEqual(len(urls), 4)
        for channel_id in [self.SMS_774, self.VOICE_774, self.SMS_632, self.VOICE_632]:
            self.assertTrue(
                any(url.endswith(f'/{channel_id}/') for url in urls),
                f'{channel_id} got no subscription: {urls}',
            )

    def test_dry_run_writes_nothing(self):
        post = self._run()
        self.assertEqual(VirtualNumber.objects.count(), 0)
        self.assertFalse(post.called)


@override_settings(
    BIRD_WEBHOOK_SIGNING_KEY='test-signing-key',
    BIRD_WEBHOOK_BASE_URL='https://example.test',
    BIRD_WEBHOOK_REQUIRE_SIGNATURE=True,
)
class WebhookSignatureTests(TestCase):
    """The endpoints bridge calls to arbitrary numbers, so an unsigned POST
    from anyone must not be enough to drive them."""

    PATH = '/webhook/bird/voice/aaaaaaaa-0000-4000-8000-000000000001/'

    def _body(self):
        return json.dumps({'payload': {
            'id': 'call-1', 'from': '+61411111111', 'status': 'starting',
        }})

    def _sign(self, body, timestamp):
        signed = b'\n'.join([
            str(timestamp).encode(),
            f'https://example.test{self.PATH}'.encode(),
            hashlib.sha256(body.encode()).digest(),
        ])
        digest = hmac.new(b'test-signing-key', signed, hashlib.sha256).digest()
        return base64.b64encode(digest).decode()

    def _post(self, headers):
        # Accepted requests run the full view; never let one reach Bird.
        with patch('blog.bird_webhooks.requests.post') as bird:
            response = Client().post(
                self.PATH, data=self._body(),
                content_type='application/json', headers=headers,
            )
        self.bird_called = bird.called
        return response

    def test_valid_signature_is_accepted(self):
        body, ts = self._body(), int(time.time())
        response = self._post({
            'messagebird-signature': self._sign(body, ts),
            'messagebird-request-timestamp': str(ts),
        })
        self.assertNotEqual(response.status_code, 403)

    def test_unsigned_request_is_rejected(self):
        self.assertEqual(self._post({}).status_code, 403)

    def test_wrong_signature_is_rejected(self):
        response = self._post({
            'messagebird-signature': base64.b64encode(b'nope').decode(),
            'messagebird-request-timestamp': str(int(time.time())),
        })
        self.assertEqual(response.status_code, 403)

    def test_replayed_old_request_is_rejected(self):
        stale = int(time.time()) - 3600
        response = self._post({
            'messagebird-signature': self._sign(self._body(), stale),
            'messagebird-request-timestamp': str(stale),
        })
        self.assertEqual(response.status_code, 403)

    @override_settings(BIRD_WEBHOOK_SIGNING_KEY='')
    def test_verification_is_skipped_when_no_key_configured(self):
        self.assertNotEqual(self._post({}).status_code, 403)

    @override_settings(BIRD_WEBHOOK_REQUIRE_SIGNATURE=False)
    def test_rollout_mode_serves_requests_it_cannot_verify(self):
        """Signatures cover the URL, so a base-URL mismatch would take every
        call down at once. Until enforcement is switched on, log and serve."""
        self.assertNotEqual(self._post({}).status_code, 403)

        response = self._post({
            'messagebird-signature': base64.b64encode(b'nope').decode(),
            'messagebird-request-timestamp': str(int(time.time())),
        })
        self.assertNotEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# View: driver_login
# ---------------------------------------------------------------------------

class DriverLoginViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('blog:driver_login')
        self.user = make_user(username='drv1', password='TestPass1!')
        self.driver = make_driver(user=self.user)

    def test_get_login_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'basecamp/driver/login.html')

    def test_redirect_if_already_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('blog:driver_dashboard'))

    def test_login_with_invalid_credentials(self):
        response = self.client.post(self.url, {
            'username': 'drv1',
            'password': 'wrong',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect username or password')

    def test_login_success_redirects_to_dashboard(self):
        response = self.client.post(self.url, {
            'username': 'drv1',
            'password': 'TestPass1!',
        })
        self.assertRedirects(response, reverse('blog:driver_dashboard'))

    def test_login_must_change_password_redirects(self):
        self.driver.must_change_password = True
        self.driver.save()
        response = self.client.post(self.url, {
            'username': 'drv1',
            'password': 'TestPass1!',
        })
        self.assertRedirects(response, reverse('blog:driver_change_password'))

    def test_login_user_without_driver_shows_error(self):
        no_driver_user = make_user(username='nodrvr', password='Pass9999!')
        response = self.client.post(self.url, {
            'username': 'nodrvr',
            'password': 'Pass9999!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No driver account')


# ---------------------------------------------------------------------------
# View: driver_logout
# ---------------------------------------------------------------------------

class DriverLogoutViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.driver = make_driver(user=self.user)
        self.client.force_login(self.user)

    def test_logout_redirects_to_login(self):
        url = reverse('blog:driver_logout')
        response = self.client.post(url)
        self.assertRedirects(response, reverse('blog:driver_login'))

    def test_logout_get_not_allowed(self):
        url = reverse('blog:driver_logout')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


# ---------------------------------------------------------------------------
# View: driver_dashboard
# ---------------------------------------------------------------------------

class DriverDashboardViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('blog:driver_dashboard')

    def test_redirects_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, '/driver/login/?next=/driver/')

    def test_redirects_user_without_driver(self):
        user = make_user(username='nodrv', password='pass1234!')
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('blog:driver_login'))

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_dashboard_loads_for_driver(self, mock_close, mock_create):
        user = make_user(username='drv2', password='TestPass1!')
        driver = make_driver(user=user)
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'basecamp/driver/dashboard.html')

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_dashboard_context_contains_driver(self, mock_close, mock_create):
        user = make_user(username='drv3', password='TestPass1!')
        driver = make_driver(user=user)
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.context['driver'], driver)

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_dashboard_totals_are_zero_with_no_posts(self, mock_close, mock_create):
        user = make_user(username='drv4', password='TestPass1!')
        make_driver(user=user)
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.context['current_grand_total'], Decimal('0'))

    def _past_post(self, driver, days_ago, price='190'):
        with patch('blog.bird_proxy.create_bird_mapping', return_value=True), \
             patch('blog.bird_proxy.close_bird_mapping', return_value=True):
            return Post.objects.create(
                name='Pax', email='p@x.com', no_of_passenger='1',
                price=price, driver=driver, use_proxy=False,
                pickup_date=datetime.date.today() - datetime.timedelta(days=days_ago),
                pickup_time='15:00',
            )

    def _settle_day(self, driver, post, number):
        """Same-day settlement, the shape create_daily_settlements produces."""
        with patch('blog.services.settlement_service.generate_settlement_number',
                   return_value=number):
            from blog.services.settlement_service import SettlementService
            return SettlementService.create_settlement(
                driver, post.pickup_date, post.pickup_date, user=None,
            )

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_settled_past_trip_stays_in_timeline(self, mock_close, mock_create):
        """A trip must not vanish from the history the night it gets settled.

        create_daily_settlements settles each individual driver's day at 23:55,
        so on the old 'between the last two settlements' window a driver woke up
        to an empty Past Trips list (2026-08 Don). Being settled must not remove
        the row — the history is a record of work done, not of what is owed.
        """
        user = make_user(username='tl1', password='TestPass1!')
        driver = make_driver(user=user)
        post = self._past_post(driver, days_ago=3)
        settlement = self._settle_day(driver, post, 'TEST-TL1-SET-01')
        self.assertIsNotNone(settlement)

        self.client.force_login(user)
        timeline = self.client.get(self.url).context['timeline']

        trips = [i for i in timeline if i['type'] == 'trip']
        self.assertEqual([i['data'].pk for i in trips], [post.pk])

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_daily_settlements_do_not_truncate_older_history(self, mock_close, mock_create):
        """Two same-day settlements used to cut history down to the days between
        them — everything older disappeared. All three trips must survive."""
        user = make_user(username='tl2', password='TestPass1!')
        driver = make_driver(user=user)
        old = self._past_post(driver, days_ago=40)
        mid = self._past_post(driver, days_ago=6)
        recent = self._past_post(driver, days_ago=2)
        self._settle_day(driver, mid, 'TEST-TL2-SET-01')
        self._settle_day(driver, recent, 'TEST-TL2-SET-02')

        self.client.force_login(user)
        timeline = self.client.get(self.url).context['timeline']

        trips = {i['data'].pk for i in timeline if i['type'] == 'trip'}
        self.assertEqual(trips, {old.pk, mid.pk, recent.pk})

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_unsettled_trip_on_settlement_date_still_owed(self, mock_close, mock_create):
        """A trip added after that day's settlement ran keeps counting as owed —
        the old 'pickup_date > to_date' cut silently dropped it from the balance."""
        user = make_user(username='tl3', password='TestPass1!')
        driver = make_driver(user=user)
        settled = self._past_post(driver, days_ago=2, price='190')
        self._settle_day(driver, settled, 'TEST-TL3-SET-01')
        latecomer = self._past_post(driver, days_ago=2, price='110')
        latecomer.paid = '110'
        latecomer.save()

        self.client.force_login(user)
        context = self.client.get(self.url).context

        # driver_price defaults to price − 10 → only the unsettled 110 job counts.
        self.assertEqual(context['to_be_paid'], Decimal('100'))


# ---------------------------------------------------------------------------
# View: driver_change_password
# ---------------------------------------------------------------------------

class DriverChangePasswordViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('blog:driver_change_password')

    def test_get_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, '/driver/login/?next=/driver/change-password/')

    def test_get_renders_form(self):
        user = make_user(username='cp1', password='OldPass1!')
        make_driver(user=user, must_change_password=True)
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_password_mismatch_shows_error(self):
        user = make_user(username='cp2', password='OldPass1!')
        make_driver(user=user, must_change_password=True)
        self.client.force_login(user)
        response = self.client.post(self.url, {
            'new_password': 'NewPass99!',
            'confirm_password': 'Different!',
        })
        self.assertContains(response, 'do not match')

    def test_password_change_success_redirects_to_dashboard(self):
        user = make_user(username='cp3', password='OldPass1!')
        driver = make_driver(user=user, must_change_password=True)
        self.client.force_login(user)
        response = self.client.post(self.url, {
            'new_password': 'NewValidP@ss1!',
            'confirm_password': 'NewValidP@ss1!',
        })
        self.assertRedirects(response, reverse('blog:driver_dashboard'))
        driver.refresh_from_db()
        self.assertFalse(driver.must_change_password)


# ---------------------------------------------------------------------------
# View: driver_impersonate (staff-only)
# ---------------------------------------------------------------------------

class DriverImpersonateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_superuser('staff', 'staff@x.com', 'StaffPass1!')
        self.user = make_user(username='imp1', password='ImpPass1!')
        self.driver = make_driver(user=self.user)

    def test_non_staff_cannot_impersonate(self):
        regular = make_user(username='reg', password='RegPass1!')
        self.client.force_login(regular)
        url = reverse('blog:driver_impersonate', args=[self.driver.pk])
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

    def test_staff_impersonates_driver(self):
        self.client.force_login(self.staff)
        url = reverse('blog:driver_impersonate', args=[self.driver.pk])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('blog:driver_dashboard'))
        self.assertIn('impersonator_id', self.client.session)


# ---------------------------------------------------------------------------
# Settlement GST (Option A — driver.gst_registered drives GST, not ABN)
# ---------------------------------------------------------------------------

class SettlementGstTests(TestCase):

    def setUp(self):
        from blog.services.settlement_service import SettlementService
        self.SettlementService = SettlementService
        self.admin = User.objects.create_superuser('gstadmin', 'g@x.com', 'pass')
        self.region = make_region()
        self.from_date = datetime.date.today()
        self.to_date = datetime.date.today() + datetime.timedelta(days=6)
        self.pickup = self.from_date + datetime.timedelta(days=1)

    def _make_post(self, driver, price, cash=False):
        # patch bird proxy so Post.save side-effects stay offline
        with patch('blog.bird_proxy.create_bird_mapping', return_value=True), \
             patch('blog.bird_proxy.close_bird_mapping', return_value=True):
            return Post.objects.create(
                name='Pax', email='p@x.com', no_of_passenger='1',
                price=str(price), cash=cash, driver=driver,
                pickup_date=self.pickup, pickup_time='10:00',
            )

    def _settle(self, driver):
        # One-step flow: create_settlement records the expense immediately.
        # settlement-number generation depends on region/airport config that is
        # irrelevant to GST behaviour — stub it with a unique value.
        number = f"TEST-SET-{driver.pk}"
        with patch('blog.services.settlement_service.generate_settlement_number',
                   return_value=number):
            settlement = self.SettlementService.create_settlement(
                driver, self.from_date, self.to_date, user=self.admin
            )
        settlement.refresh_from_db()
        return settlement

    def test_registered_driver_gets_gst_and_gst_transaction(self):
        from accounting.models import Transaction
        driver = make_driver(user=make_user('reg_drv'), region=self.region)
        driver.gst_registered = True
        driver.save()
        self._make_post(driver, '110', cash=False)   # bank-paid → counts toward paid_total

        settlement = self._settle(driver)

        item = settlement.items.first()
        self.assertEqual(item.gst_amount, Decimal('10.00'))   # 110 / 11
        self.assertEqual(settlement.gst_total, Decimal('10.00'))

        tx = Transaction.objects.get(category='subcontract',
                                     description=settlement.settlement_number)
        self.assertEqual(tx.gst_code, 'gst')
        self.assertEqual(tx.gst_amount, Decimal('10.00'))
        self.assertEqual(tx.direction, 'expense')
        self.assertEqual(tx.gross_amount, settlement.paid_total)

    def test_unregistered_driver_zero_gst_and_no_gst_transaction(self):
        from accounting.models import Transaction
        driver = make_driver(user=make_user('unreg_drv'), region=self.region)
        self.assertFalse(driver.gst_registered)   # default
        self._make_post(driver, '110', cash=False)

        settlement = self._settle(driver)

        item = settlement.items.first()
        self.assertEqual(item.gst_amount, Decimal('0'))
        self.assertEqual(settlement.gst_total, Decimal('0'))

        tx = Transaction.objects.get(category='subcontract',
                                     description=settlement.settlement_number)
        self.assertEqual(tx.gst_code, 'no_gst')
        self.assertEqual(tx.gst_amount, Decimal('0'))

    def test_driver_collected_cash_excluded_from_settlement(self):
        # Customer paid the driver directly in cash — money never touched the
        # company, so it must not create a settlement item/payout at all.
        driver = make_driver(user=make_user('dcc_drv'), region=self.region)
        post = self._make_post(driver, '130', cash=True)
        post.driver_collected_cash = True
        post.save()

        number = f"TEST-SET-DCC-{driver.pk}"
        with patch('blog.services.settlement_service.generate_settlement_number',
                   return_value=number):
            settlement = self.SettlementService.create_settlement(
                driver, self.from_date, self.to_date, user=self.admin
            )

        self.assertIsNone(settlement)
        self.assertEqual(DriverSettlementItem.objects.filter(post=post).count(), 0)

    def test_resync_creates_single_transaction(self):
        from accounting.models import Transaction
        from blog.services.settlement_service import sync_settlement_expense
        driver = make_driver(user=make_user('dup_drv'), region=self.region)
        driver.gst_registered = True
        driver.save()
        self._make_post(driver, '220', cash=False)

        settlement = self._settle(driver)
        # re-syncing (e.g. after an edit) must upsert, never duplicate.
        sync_settlement_expense(settlement)

        count = Transaction.objects.filter(
            category='subcontract',
            description=settlement.settlement_number,
        ).count()
        self.assertEqual(count, 1)


# ---------------------------------------------------------------------------
# Agreement: invoice email
# ---------------------------------------------------------------------------

class AgreementConsentTests(TestCase):
    """The agreement collects the address invoices/receipts are emailed to.
    Nobody who has already signed is re-prompted on their own."""

    def setUp(self):
        from blog.driver_views import _confirmed_agreement
        self._confirmed_agreement = _confirmed_agreement
        self.region = make_region()
        self.driver = make_driver(user=make_user('agr_drv'), region=self.region)
        self.client.force_login(self.driver.user)

    def _sign(self, **extra):
        data = {
            'company_name': 'Drv Pty Ltd', 'abn': '11 111 111 111',
            'invoice_email': 'invoices@drv.example.com',
            'item_status_confirmed': 'on',
            'item_liability_confirmed': 'on',
        }
        data.update(extra)
        return self.client.post(reverse('blog:driver_agreement'), data)

    def test_signing_records_invoice_email(self):
        self._sign()
        self.assertIsNotNone(self._confirmed_agreement(self.driver))
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.driver_email, 'invoices@drv.example.com')
        self.assertEqual(self.driver.business_name, 'Drv Pty Ltd')

    def test_invoice_email_required(self):
        response = self._sign(invoice_email='')
        self.assertContains(response, 'email address your invoices should go to')
        self.assertIsNone(self._confirmed_agreement(self.driver))

    def test_invoice_email_must_be_valid(self):
        response = self._sign(invoice_email='not-an-email')
        self.assertContains(response, 'valid email address')
        self.assertIsNone(self._confirmed_agreement(self.driver))

    def test_signed_driver_is_not_re_prompted_when_gst_turned_on(self):
        # Staff ticking GST later must not reopen the agreement — re-collecting
        # consent is done manually (delete the row, send the link).
        self._sign()
        self.driver.gst_registered = True
        self.driver.save(update_fields=['gst_registered'])
        self.assertIsNotNone(self._confirmed_agreement(self.driver))
        response = self.client.get(reverse('blog:driver_agreement'))
        self.assertTemplateUsed(response, 'basecamp/driver/agreement_done.html')


# ---------------------------------------------------------------------------
# Command: arrival_reminder (도착 1시간 전 리마인더)
# ---------------------------------------------------------------------------

class ArrivalReminderTests(TestCase):
    """도착 손님은 아침 메일을 비행 중이라 못 본다. 이 메일이 그 자리를 대신하므로,
    한 번은 반드시 나가야 하고 두 번은 절대 나가면 안 된다."""

    TZ = pytz.timezone('Australia/Sydney')

    def setUp(self):
        self.region = make_region()
        self.now = self.TZ.localize(datetime.datetime(2026, 8, 2, 9, 0))

    def make_arrival(self, flight_time='10:00', **kwargs):
        fields = dict(
            name='Arriving Guest',
            email='guest@example.com',
            no_of_passenger='2',
            price='100',
            paid='100',  # 미결제 건은 notify_user_post 시그널이 pending=True 로 만들어 대상에서 빠진다
            region=self.region,
            pickup_date=self.now.date(),
            direction='Pickup from Intl Airport',
            flight_number='KE121',
            flight_time=flight_time,
            pickup_time='10:45',
        )
        fields.update(kwargs)
        return Post.objects.create(**fields)

    def run_command(self, *args, now=None):
        module = 'blog.management.commands.arrival_reminder'
        with patch(f'{module}.current_time', return_value=now or self.now), \
             patch(f'{module}.booking_helper.update_meeting_point_for_arrivals'), \
             patch(f'{module}.assign_default_driver_if_missing', return_value=None), \
             patch(f'{module}.send_telegram_sync'):
            call_command('arrival_reminder', *args, stdout=StringIO())

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_sends_one_hour_before_scheduled_arrival(self, *_):
        post = self.make_arrival(flight_time='10:00')  # now=09:00 → 정확히 창 시작
        self.run_command()
        post.refresh_from_db()
        self.assertIsNotNone(post.arrival_reminder_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('guest@example.com', mail.outbox[0].to)

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_not_sent_before_the_window_opens(self, *_):
        post = self.make_arrival(flight_time='14:00')  # now=09:00 → 아직 5시간 전
        self.run_command()
        post.refresh_from_db()
        self.assertIsNone(post.arrival_reminder_sent_at)
        self.assertEqual(mail.outbox, [])

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_second_run_does_not_resend(self, *_):
        """크론이 10분마다 도니 중복 방지가 깨지면 손님은 하루에 6통을 받는다."""
        self.make_arrival(flight_time='10:00')
        self.run_command()
        self.run_command(now=self.TZ.localize(datetime.datetime(2026, 8, 2, 9, 10)))
        self.assertEqual(len(mail.outbox), 1)

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_late_run_still_sends(self, *_):
        """크론이 멈췄다 살아나면 늦게라도 보내야 한다 — 조용히 건너뛰면 안 된다."""
        self.make_arrival(flight_time='10:00')
        self.run_command(now=self.TZ.localize(datetime.datetime(2026, 8, 2, 11, 30)))
        self.assertEqual(len(mail.outbox), 1)

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_falls_back_to_pickup_time_when_flight_time_missing(self, *_):
        """flight_time이 비었다고 스킵하면 그 손님은 당일 메일을 아예 못 받는다."""
        self.make_arrival(flight_time='', pickup_time='09:30')
        self.run_command()
        self.assertEqual(len(mail.outbox), 1)

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_skips_cancelled_pending_and_opted_out(self, *_):
        self.make_arrival(cancelled=True)
        self.make_arrival(pending=True)
        self.make_arrival(no_email_reminder=True)
        self.run_command()
        self.assertEqual(mail.outbox, [])

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_departures_are_left_to_booking_reminder(self, *_):
        self.make_arrival(direction='Drop off to Intl Airport')
        self.run_command()
        self.assertEqual(mail.outbox, [])

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_booking_reminder_no_longer_sends_todays_arrival_mail(self, *_):
        """두 커맨드가 같은 건을 보내면 중복이다 — 당일 도착은 arrival_reminder 전담."""
        self.make_arrival()
        with patch('blog.management.commands.booking_reminder.booking_helper'
                   '.update_meeting_point_for_arrivals'), \
             patch('blog.management.commands.booking_reminder.send_telegram_sync'):
            call_command('booking_reminder', '--today', stdout=StringIO())
        self.assertEqual(mail.outbox, [])

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_meeting_point_mail_renders(self, *_):
        """미팅포인트가 배정된 건은 driver_details 템플릿으로 나간다 — 실제 도착 손님이
        가장 많이 받는 경로라 렌더링이 깨지면 당일 메일이 통째로 사라진다."""
        from regions.models import Airport, Country, Terminal, TerminalPickupPoint

        airport = Airport.objects.create(
            country=Country.objects.create(name='Australia'), city='Sydney', code='SYD',
        )
        self.region.airports.add(airport)
        terminal = Terminal.objects.create(
            airport=airport, name='T1', type=Terminal.TerminalType.INTL,
        )
        point = TerminalPickupPoint.objects.create(
            terminal=terminal, name='Public Pickup', is_default_point=True,
            instruction='Meet the driver at the Public Pickup zone.',
        )
        post = self.make_arrival(terminal_pickup_point=point)

        self.run_command()
        post.refresh_from_db()
        self.assertIsNotNone(post.arrival_reminder_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Public Pickup zone', mail.outbox[0].body)

    @patch('blog.bird_proxy.create_bird_mapping', return_value=True)
    @patch('blog.bird_proxy.close_bird_mapping', return_value=True)
    def test_idle_run_touches_nothing(self, *_):
        """몇 분마다 도는 커맨드다 — 보낼 게 없는 대부분의 실행은 조회만 하고 끝나야
        한다(미팅포인트 갱신은 DB 저장 + 캘린더 동기화를 유발한다)."""
        self.make_arrival(flight_time='14:00')  # now=09:00 → 아직 대상 아님
        module = 'blog.management.commands.arrival_reminder'
        with patch(f'{module}.current_time', return_value=self.now), \
             patch(f'{module}.booking_helper.update_meeting_point_for_arrivals') as update_points, \
             patch(f'{module}.send_telegram_sync'):
            call_command('arrival_reminder', stdout=StringIO())
        update_points.assert_not_called()
        self.assertEqual(mail.outbox, [])


# ---------------------------------------------------------------------------
# 발송 실패 알림 (2026-08-16 SMTP 자격증명 만료로 4시간 40분간 전 메일이
# 조용히 죽은 뒤 추가). 크론 커맨드는 실패해도 로그에만 남아서, 알림이 없으면
# 장애를 며칠씩 모른다.
# ---------------------------------------------------------------------------
class _Boom(Exception):
    pass


class MixinTests(TestCase):
    def _cmd(self, header='테스트 실패'):
        class C(TelegramAlertMixin, BaseCommand):
            alert_header = header

            def handle(self, *a, **kw):
                for m in getattr(self, '_todo', []):
                    self.alerts.append(m)
                if getattr(self, '_raise', False):
                    raise _Boom('db gone')
        return C()

    def test_flush_on_normal_completion(self):
        c = self._cmd()
        c._todo = ['❌ a', '❌ b']
        with patch('utils.command_alerts.send_telegram_sync') as tg:
            c.run_from_argv(['manage.py', 'x'])
        msg = tg.call_args_list[0].args[0]
        print('\n[정상 종료]\n' + msg)
        self.assertIn('⚠️ 테스트 실패 2건', msg)

    def test_no_alert_when_clean(self):
        c = self._cmd()
        with patch('utils.command_alerts.send_telegram_sync') as tg:
            c.run_from_argv(['manage.py', 'x'])
        self.assertEqual(tg.call_count, 0)

    def test_flush_even_when_command_crashes(self):
        c = self._cmd()
        c._todo = ['❌ 먼저 실패한 건']
        c._raise = True
        with patch('utils.command_alerts.send_telegram_sync') as tg:
            with self.assertRaises(_Boom):
                c.run_from_argv(['manage.py', 'x'])
        msg = tg.call_args_list[0].args[0]
        print('\n[커맨드 중단]\n' + msg)
        self.assertIn('먼저 실패한 건', msg)
        self.assertIn('💥 커맨드 중단 | _Boom: db gone', msg)

    def test_lines_capped_and_cleared(self):
        c = self._cmd()
        c._todo = [f'❌ {i}' for i in range(14)]
        with patch('utils.command_alerts.send_telegram_sync') as tg:
            c.run_from_argv(['manage.py', 'x'])
        self.assertIn('…외 4건', tg.call_args_list[0].args[0])
        c.flush_alerts()                       # 두 번째 호출은 조용해야 한다
        self.assertEqual(tg.call_count, 1)

    def test_no_header_keeps_raw_lines(self):
        c = self._cmd(header=None)
        c._todo = ['⏰ 지연 발송 30분']
        with patch('utils.command_alerts.send_telegram_sync') as tg:
            c.run_from_argv(['manage.py', 'x'])
        self.assertEqual(tg.call_args_list[0].args[0], '⏰ 지연 발송 30분')


class ConvertedCommandsTests(TestCase):
    def test_all_targets_have_mixin_and_header(self):
        from importlib import import_module
        names = ['send_final_warning', 'confirm_booking', 'check_detail',
                 'check_flight_no', 'send_arrivals', 'double_check_calendar']
        for n in names:
            cmd = import_module(f'blog.management.commands.{n}').Command
            self.assertTrue(issubclass(cmd, TelegramAlertMixin), n)
            self.assertTrue(cmd.alert_header, n)
        print('\n믹스인 적용 확인:', ', '.join(names))

    def test_confirm_booking_alerts_and_continues(self):
        for n in ('alice', 'bob'):
            Post.objects.create(name=n, email=f'{n}@example.com', no_of_passenger='2',
                                pickup_date=timezone.localdate() + timedelta(days=3))
        with patch('blog.management.commands.confirm_booking.send_template_email',
                   side_effect=Exception('535 BadCredentials')) as se, \
             patch('utils.command_alerts.send_telegram_sync') as tg:
            call_command('confirm_booking')
        msg = tg.call_args_list[0].args[0]
        print('\n[confirm_booking]\n' + msg)
        self.assertEqual(se.call_count, 2)          # 첫 실패로 루프가 끊기지 않는다
        self.assertIn('confirm_booking 실패 2건', msg)


class BookingReminderMissingTests(TestCase):
    def _make(self, name, offset, **kw):
        d = dict(name=name, email=f'{name}@example.com', no_of_passenger='2',
                 pickup_date=timezone.localdate() + timedelta(days=offset),
                 pickup_time='10:00', direction='Drop off to Intl Airport')
        d.update(kw)
        p = Post.objects.create(**d)
        Post.objects.filter(pk=p.pk).update(pending=False)
        return p

    def _run(self):
        with patch('utils.booking_helper.update_meeting_point_for_arrivals'), \
             patch('blog.management.commands.booking_reminder.send_telegram_sync') as tg:
            call_command('booking_reminder')
            return [c.args[0] for c in tg.call_args_list]

    def test_detects_missing_in_every_stage(self):
        self._make('today', 0)
        self._make('tomorrow', 1)
        self._make('review', -5)
        with patch('blog.management.commands.booking_reminder.send_template_email',
                   side_effect=Exception('535 BadCredentials')):
            msgs = self._run()
        joined = '\n'.join(msgs)
        print('\n[전 단계 누락 탐지]\n' + joined)
        self.assertIn('Reminder-Today 누락 1건', joined)
        self.assertIn('Reminder-Tomorrow 누락 1건', joined)
        self.assertIn('Review-EasyGo 누락 1건', joined)

    def test_opted_out_is_not_reported(self):
        self._make('optout', 0, no_email_reminder=True)
        with patch('blog.management.commands.booking_reminder.send_template_email'):
            msgs = self._run()
        print('\n[수신거부 오탐 여부] telegram calls =', len(msgs))
        self.assertEqual(msgs, [])

    def test_silent_when_all_sent(self):
        self._make('ok', 0)
        with patch('blog.management.commands.booking_reminder.send_template_email'):
            msgs = self._run()
        self.assertEqual(msgs, [])


# ---------------------------------------------------------------------------
# Command: create_daily_settlements
# ---------------------------------------------------------------------------

class CreateDailySettlementsTests(TestCase):
    """Only drivers who are actually paid off at the end of each day may be
    auto-settled. Settling a driver who is paid weekly/monthly books money that
    never moved, and the trip then drops out of what their dashboard says they
    are owed (2026-08 Don)."""

    def setUp(self):
        self.today = datetime.date.today()

    def _driver(self, username, **kwargs):
        driver = make_driver(user=make_user(username), region=make_region())
        for field, value in kwargs.items():
            setattr(driver, field, value)
        driver.save()
        return driver

    def _post(self, driver):
        with patch('blog.bird_proxy.create_bird_mapping', return_value=True), \
             patch('blog.bird_proxy.close_bird_mapping', return_value=True):
            return Post.objects.create(
                name='Pax', email='p@x.com', no_of_passenger='1',
                price='190', driver=driver,
                pickup_date=self.today, pickup_time='15:00',
            )

    def _run(self):
        with patch('blog.services.settlement_service.generate_settlement_number',
                   side_effect=lambda d, to_date, seq: f'TEST-{d.pk}-{seq}'):
            call_command('create_daily_settlements', '--date', self.today.isoformat())

    def test_settles_daily_driver(self):
        driver = self._driver('daily_drv', settle_daily=True)
        self._post(driver)
        self._run()
        self.assertEqual(DriverSettlement.objects.filter(driver=driver).count(), 1)

    def test_skips_driver_settled_in_batches(self):
        driver = self._driver('monthly_drv', settle_daily=False)
        self._post(driver)
        self._run()
        self.assertFalse(DriverSettlement.objects.filter(driver=driver).exists())

    def test_skips_company(self):
        driver = self._driver('company_drv', is_company=True)
        self._post(driver)
        self._run()
        self.assertFalse(DriverSettlement.objects.filter(driver=driver).exists())
