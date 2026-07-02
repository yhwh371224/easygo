"""
Tests for the regions app: models, views, and business logic.
"""
import datetime
from unittest.mock import patch, AsyncMock

from django.test import TestCase, Client, override_settings
from django.urls import reverse

from regions.models import Region, Country, Airport, Terminal, RegionSuburb, RequestLog
from basecamp.modules.date_utils import parse_date, parse_booking_dates
from basecamp.modules.view_helpers import is_duplicate_submission, get_customer_status
from blog.blog_utils import get_default_driver_for_region


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_region(slug='test-region', name='Test Region', is_active=True, is_coming_soon=False):
    return Region.objects.create(
        slug=slug,
        name=name,
        timezone='Australia/Sydney',
        phone='0200000000',
        is_active=is_active,
        is_coming_soon=is_coming_soon,
        arrival_guide='Step 1\nStep 2\nStep 3',
    )


def make_country(name='Testland'):
    return Country.objects.get_or_create(name=name)[0]


def make_airport(code='TST', city='Test City', country=None):
    if country is None:
        country = make_country()
    return Airport.objects.get_or_create(code=code, defaults={'city': city, 'country': country})[0]


FUTURE = (datetime.date.today() + datetime.timedelta(days=7)).strftime('%Y-%m-%d')
RETURN_FUTURE = (datetime.date.today() + datetime.timedelta(days=14)).strftime('%Y-%m-%d')
PAST = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')


# ---------------------------------------------------------------------------
# Model: Region
# ---------------------------------------------------------------------------

class RegionModelTests(TestCase):

    def test_create_and_str(self):
        region = make_region()
        self.assertEqual(str(region), 'Test Region')

    def test_is_active_default_true(self):
        r = Region.objects.create(slug='test-perth', name='Test Perth', timezone='Australia/Perth', phone='000')
        self.assertTrue(r.is_active)

    def test_is_coming_soon_default_false(self):
        r = make_region(slug='test-not-coming', name='Test Not Coming')
        self.assertFalse(r.is_coming_soon)

    def test_unique_slug(self):
        make_region(slug='test-dup-slug', name='Dup Test City')
        with self.assertRaises(Exception):
            make_region(slug='test-dup-slug', name='Dup Test City 2')

    def test_ordering_by_name(self):
        make_region(slug='zoo', name='Zzz City')
        make_region(slug='aaa', name='Aaa City')
        names = list(Region.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))


# ---------------------------------------------------------------------------
# Model: Country
# ---------------------------------------------------------------------------

class CountryModelTests(TestCase):

    def test_create_and_str(self):
        c = Country.objects.create(name='New Zealand')
        self.assertEqual(str(c), 'New Zealand')

    def test_unique_name(self):
        Country.objects.create(name='Unique Country')
        with self.assertRaises(Exception):
            Country.objects.create(name='Unique Country')


# ---------------------------------------------------------------------------
# Model: Airport
# ---------------------------------------------------------------------------

class AirportModelTests(TestCase):

    def test_create_and_str(self):
        airport = make_airport()
        self.assertIn('TST', str(airport))
        self.assertIn('Test City', str(airport))

    def test_unique_code(self):
        make_airport(code='T99', city='Test 99')
        with self.assertRaises(Exception):
            Airport.objects.create(code='T99', city='Test 99 dup', country=make_country())

    def test_ordering_by_code(self):
        make_airport(code='ZZZ', city='Z City')
        make_airport(code='AAA', city='A City')
        codes = list(Airport.objects.values_list('code', flat=True))
        self.assertEqual(codes, sorted(codes))


# ---------------------------------------------------------------------------
# Model: Terminal
# ---------------------------------------------------------------------------

class TerminalModelTests(TestCase):

    def setUp(self):
        self.airport = make_airport()

    def test_create_terminal(self):
        t = Terminal.objects.create(
            airport=self.airport,
            name='T1',
            type=Terminal.TerminalType.INTL,
        )
        self.assertIn('TST', str(t))
        self.assertIn('T1', str(t))

    def test_unique_together(self):
        Terminal.objects.create(airport=self.airport, name='T1', type=Terminal.TerminalType.INTL)
        with self.assertRaises(Exception):
            Terminal.objects.create(airport=self.airport, name='T1', type=Terminal.TerminalType.INTL)

    def test_different_type_allowed(self):
        Terminal.objects.create(airport=self.airport, name='T1', type=Terminal.TerminalType.INTL)
        t2 = Terminal.objects.create(airport=self.airport, name='T1', type=Terminal.TerminalType.DOMESTIC)
        self.assertEqual(t2.type, 'domestic')

    def test_get_type_display(self):
        t = Terminal.objects.create(airport=self.airport, name='T2', type=Terminal.TerminalType.INTL)
        self.assertEqual(t.get_type_display(), 'International')


# ---------------------------------------------------------------------------
# Model: RegionSuburb
# ---------------------------------------------------------------------------

class RegionSuburbModelTests(TestCase):

    def setUp(self):
        self.region = make_region()

    def test_create_suburb(self):
        s = RegionSuburb.objects.create(
            region=self.region,
            name='Parramatta',
            slug='parramatta',
            price=65.00,
            zone='Zone 2',
        )
        self.assertEqual(str(s), 'Test Region — Parramatta')

    def test_unique_together_region_slug(self):
        RegionSuburb.objects.create(region=self.region, name='CBD', slug='cbd', price=50, zone='Z1')
        with self.assertRaises(Exception):
            RegionSuburb.objects.create(region=self.region, name='CBD2', slug='cbd', price=60, zone='Z1')

    def test_same_slug_different_regions(self):
        region2 = make_region(slug='test-region-2', name='Test Region 2')
        RegionSuburb.objects.create(region=self.region, name='CBD', slug='cbd', price=50, zone='Z1')
        s2 = RegionSuburb.objects.create(region=region2, name='CBD', slug='cbd', price=45, zone='Z1')
        self.assertEqual(s2.region.name, 'Test Region 2')

    def test_is_active_default_true(self):
        s = RegionSuburb.objects.create(region=self.region, name='Hills', slug='hills', price=80, zone='Z3')
        self.assertTrue(s.is_active)

    def test_featured_defaults(self):
        s = RegionSuburb.objects.create(region=self.region, name='Ryde', slug='ryde', price=70, zone='Z2')
        self.assertFalse(s.is_featured)
        self.assertEqual(s.featured_order, 999)


# ---------------------------------------------------------------------------
# Model: RequestLog
# ---------------------------------------------------------------------------

class RequestLogModelTests(TestCase):

    def test_create_request_log(self):
        region = make_region()
        log = RequestLog.objects.create(
            region=region,
            path='/sydney/booking/',
            ip='1.2.3.4',
            user_agent='Mozilla/5.0',
        )
        self.assertEqual(log.ip, '1.2.3.4')
        self.assertEqual(log.region.slug, 'test-region')

    def test_ordering_newest_first(self):
        region = make_region()
        l1 = RequestLog.objects.create(region=region, path='/a/', ip='1.1.1.1')
        l2 = RequestLog.objects.create(region=region, path='/b/', ip='2.2.2.2')
        qs = list(RequestLog.objects.all())
        self.assertEqual(qs[0].pk, l2.pk)


# ---------------------------------------------------------------------------
# View: region_home
# ---------------------------------------------------------------------------

class RegionHomeViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.region = make_region(slug='test-home', name='Test Home City')

    def test_active_region_returns_200(self):
        url = reverse('regions:home', kwargs={'region_slug': 'test-home'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'regions/pages/home.html')

    def test_inactive_region_returns_404(self):
        make_region(slug='test-inactive', name='Inactive City', is_active=False)
        url = reverse('regions:home', kwargs={'region_slug': 'test-inactive'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_coming_soon_renders_coming_soon_template(self):
        make_region(slug='test-coming', name='Coming City', is_coming_soon=True)
        url = reverse('regions:home', kwargs={'region_slug': 'test-coming'})
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'regions/pages/coming_soon.html')

    def test_context_contains_region(self):
        url = reverse('regions:home', kwargs={'region_slug': 'test-home'})
        response = self.client.get(url)
        self.assertEqual(response.context['region'].slug, 'test-home')

    def test_featured_suburbs_limited_to_seven(self):
        for i in range(10):
            RegionSuburb.objects.create(
                region=self.region,
                name=f'Suburb {i}',
                slug=f'suburb-{i}',
                price=50 + i,
                zone='Z1',
                is_active=True,
                is_featured=True,
                featured_order=i,
            )
        url = reverse('regions:home', kwargs={'region_slug': 'test-home'})
        response = self.client.get(url)
        self.assertLessEqual(len(response.context['featured_suburbs']), 7)



# ---------------------------------------------------------------------------
# View: region_confirmation
# ---------------------------------------------------------------------------

class RegionConfirmationViewTests(TestCase):

    def test_confirmation_page_returns_200(self):
        make_region(slug='test-conf', name='Conf City')
        url = reverse('regions:confirmation', kwargs={'region_slug': 'test-conf'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'regions/booking/confirmation.html')


# ---------------------------------------------------------------------------
# View: region_meeting_point
# ---------------------------------------------------------------------------

class RegionMeetingPointViewTests(TestCase):

    def test_meeting_point_returns_200(self):
        make_region(slug='test-mp', name='Meeting Point City')
        url = reverse('regions:region_meeting_point', kwargs={'region_slug': 'test-mp'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'regions/pages/meeting_point.html')

    def test_terminals_in_context(self):
        region = make_region(slug='test-mp-terms', name='Terminal City')
        region.terminal_info = [{'name': 'T1', 'info': 'Gate A'}]
        region.save()
        url = reverse('regions:region_meeting_point', kwargs={'region_slug': 'test-mp-terms'})
        response = self.client.get(url)
        self.assertEqual(len(response.context['terminals']), 1)


# ---------------------------------------------------------------------------
# View: region_arrival_guide
# ---------------------------------------------------------------------------

class RegionArrivalGuideViewTests(TestCase):

    def test_arrival_guide_steps_parsed(self):
        region = make_region(slug='test-ag', name='Arrival Guide City')
        url = reverse('regions:arrival_guide', kwargs={'region_slug': 'test-ag'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['steps'], ['Step 1', 'Step 2', 'Step 3'])

    def test_empty_arrival_guide_gives_no_steps(self):
        r = make_region(slug='test-ag-empty', name='Arrival Guide Empty')
        r.arrival_guide = ''
        r.save()
        url = reverse('regions:arrival_guide', kwargs={'region_slug': 'test-ag-empty'})
        response = self.client.get(url)
        self.assertEqual(response.context['steps'], [])


# ---------------------------------------------------------------------------
# View: airport_shuttle_suburb
# ---------------------------------------------------------------------------

class AirportShuttleSuburbViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.region = make_region(slug='test-suburb-region', name='Suburb Test City')
        self.suburb = RegionSuburb.objects.create(
            region=self.region,
            name='Chatswood',
            slug='chatswood',
            price=75.00,
            zone='North',
            is_active=True,
        )

    def test_valid_suburb_returns_200(self):
        url = reverse('regions:airport_shuttle_suburb', kwargs={
            'region_slug': 'test-suburb-region', 'suburb_slug': 'chatswood'
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'regions/pages/airport_shuttle_suburb.html')

    def test_invalid_suburb_returns_404(self):
        url = reverse('regions:airport_shuttle_suburb', kwargs={
            'region_slug': 'test-suburb-region', 'suburb_slug': 'nonexistent'
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_context_contains_suburb(self):
        url = reverse('regions:airport_shuttle_suburb', kwargs={
            'region_slug': 'test-suburb-region', 'suburb_slug': 'chatswood'
        })
        response = self.client.get(url)
        self.assertEqual(response.context['suburb'].slug, 'chatswood')

    def test_zone_suburbs_excludes_current(self):
        RegionSuburb.objects.create(
            region=self.region, name='Artarmon', slug='artarmon',
            price=70, zone='North', is_active=True
        )
        url = reverse('regions:airport_shuttle_suburb', kwargs={
            'region_slug': 'test-suburb-region', 'suburb_slug': 'chatswood'
        })
        response = self.client.get(url)
        zone_slugs = [s.slug for s in response.context['zone_suburbs']]
        self.assertNotIn('chatswood', zone_slugs)
        self.assertIn('artarmon', zone_slugs)

    def test_inactive_suburb_returns_404(self):
        RegionSuburb.objects.create(
            region=self.region, name='Hidden', slug='hidden',
            price=50, zone='North', is_active=False
        )
        url = reverse('regions:airport_shuttle_suburb', kwargs={
            'region_slug': 'test-suburb-region', 'suburb_slug': 'hidden'
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# View: region_inquiry (GET)
# ---------------------------------------------------------------------------

class RegionInquiryViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.region = make_region(slug='iqtest', name='Inquiry Test')

    def test_get_inquiry_page_returns_200(self):
        url = reverse('regions:inquiry', kwargs={'region_slug': 'iqtest'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'regions/inquiry/inquiry.html')

    @patch('regions.views.inquiry.send_telegram_notification', new_callable=AsyncMock)
    def test_post_creates_inquiry(self, mock_telegram):
        from blog.models import Inquiry
        url = reverse('regions:inquiry_details', kwargs={'region_slug': 'iqtest'})
        data = {
            'name': 'Sara',
            'contact': '0411111111',
            'email': 'sara@example.com',
            'pickup_date': FUTURE,
            'return_pickup_date': '',
            'pickup_time': '08:00',
            'direction': 'Drop off to Intl Terminal',
            'suburb': 'CBD',
            'no_of_passenger': '2',
            'cf-turnstile-response': 'XXXX',
        }
        count_before = Inquiry.objects.count()
        response = self.client.post(url, data)
        self.assertEqual(Inquiry.objects.count(), count_before + 1)


# ---------------------------------------------------------------------------
# Business logic: parse_date / parse_booking_dates
# ---------------------------------------------------------------------------

class ParseDateTests(TestCase):

    def test_valid_future_date_parses(self):
        result = parse_date(FUTURE)
        self.assertIsInstance(result, datetime.date)

    def test_past_date_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_date(PAST)

    def test_invalid_format_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_date('31/12/2099')

    def test_empty_required_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_date('', required=True)

    def test_empty_optional_returns_none(self):
        result = parse_date('', required=False)
        self.assertIsNone(result)

    def test_date_object_passes_through(self):
        d = datetime.date.today() + datetime.timedelta(days=5)
        result = parse_date(d)
        self.assertEqual(result, d)


class ParseBookingDatesTests(TestCase):

    def test_pickup_only(self):
        pickup, ret = parse_booking_dates(FUTURE, '')
        self.assertIsNotNone(pickup)
        self.assertIsNone(ret)

    def test_both_valid(self):
        pickup, ret = parse_booking_dates(FUTURE, RETURN_FUTURE)
        self.assertIsNotNone(pickup)
        self.assertIsNotNone(ret)
        self.assertGreater(ret, pickup)

    def test_return_before_pickup_raises(self):
        with self.assertRaises(ValueError):
            parse_booking_dates(RETURN_FUTURE, FUTURE)

    def test_missing_pickup_raises(self):
        with self.assertRaises(ValueError):
            parse_booking_dates('', '')


# ---------------------------------------------------------------------------
# Business logic: is_duplicate_submission
# ---------------------------------------------------------------------------

class IsDuplicateSubmissionTests(TestCase):

    def test_first_call_not_duplicate(self):
        from blog.models import Inquiry
        result = is_duplicate_submission(Inquiry, 'unique1@example.com')
        self.assertFalse(result)

    def test_second_call_is_duplicate(self):
        from blog.models import Inquiry
        is_duplicate_submission(Inquiry, 'dup@example.com')
        result = is_duplicate_submission(Inquiry, 'dup@example.com')
        self.assertTrue(result)

    def test_different_emails_not_duplicate(self):
        from blog.models import Inquiry
        is_duplicate_submission(Inquiry, 'a@example.com')
        result = is_duplicate_submission(Inquiry, 'b@example.com')
        self.assertFalse(result)

    def test_different_region_slugs_not_duplicate(self):
        from blog.models import Inquiry
        is_duplicate_submission(Inquiry, 'c@example.com', region_slug='sydney')
        result = is_duplicate_submission(Inquiry, 'c@example.com', region_slug='melbourne')
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# Business logic: get_default_driver_for_region
# ---------------------------------------------------------------------------

class GetDefaultDriverForRegionTests(TestCase):

    def setUp(self):
        from django.contrib.auth.models import User
        from blog.models import Driver
        self.region = make_region(slug='drvtest', name='Driver Test Region')
        self.user = User.objects.create_user('drvuser', password='pass1234!')
        self.driver = Driver.objects.create(
            user=self.user,
            driver_name='Default Driver',
            region=self.region,
            is_default=True,
        )

    def test_returns_default_driver_for_region(self):
        driver = get_default_driver_for_region(self.region)
        self.assertEqual(driver, self.driver)

    def test_returns_none_if_no_default_driver(self):
        region2 = make_region(slug='nodrvtest', name='No Driver Region')
        driver = get_default_driver_for_region(region2)
        self.assertIsNone(driver)

    def test_returns_none_if_driver_not_default(self):
        from django.contrib.auth.models import User
        from blog.models import Driver
        region3 = make_region(slug='nondefault', name='Non Default Region')
        user2 = User.objects.create_user('drv2user', password='pass1234!')
        Driver.objects.create(
            user=user2,
            driver_name='Non Default',
            region=region3,
            is_default=False,
        )
        driver = get_default_driver_for_region(region3)
        self.assertIsNone(driver)
