"""
Tests for the blog app: models, driver views, and business logic.

Celery tasks use transaction.on_commit which never fires inside TestCase
(the DB transaction is never committed), so email/calendar tasks are safe.
Bird proxy calls are patched where they would run synchronously.
"""
import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from blog.models import (
    VirtualNumber, Driver, DriverSettlement,
    Inquiry, Post, PaypalPayment, StripePayment, PhoneMapping,
)
from blog.models.driver import DriverSettlementItem
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

    def test_create_and_str(self):
        vn = VirtualNumber.objects.create(number='+61200000001')
        self.assertEqual(str(vn), '+61200000001')

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
