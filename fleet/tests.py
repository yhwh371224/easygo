import re
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from fleet.models import Vehicle


@patch('fleet.management.commands.check_vehicle_expiry.send_telegram_sync')
class CheckVehicleExpiryTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def make_vehicle(self, plate, **expiry_offsets):
        dates = {field: self.today + timedelta(days=d) for field, d in expiry_offsets.items()}
        return Vehicle.objects.create(make_model='Toyota Hiace', plate_number=plate, **dates)

    def test_alerts_within_30_days_and_overdue(self, send):
        self.make_vehicle('AAA111', rego_expiry_date=30, inspection_date=-2, green_slip_expiry_date=31)
        call_command('check_vehicle_expiry')
        message = send.call_args[0][0]
        self.assertIn('AAA111 등록(Rego)', message)
        self.assertIn('AAA111 검사(Inspection)', message)
        self.assertIn('2일 지남', message)
        self.assertNotIn('그린슬립', message)

    def test_no_alert_beyond_30_days(self, send):
        self.make_vehicle('BBB222', rego_expiry_date=31, green_slip_expiry_date=45)
        call_command('check_vehicle_expiry')
        send.assert_not_called()

    def test_inactive_vehicle_skipped(self, send):
        v = self.make_vehicle('CCC333', green_slip_expiry_date=7)
        v.is_active = False
        v.save()
        call_command('check_vehicle_expiry')
        send.assert_not_called()


# ── 주유 기록 (텔레그램 드라이버 봇) ─────────────────────────────────────────
import json as _json
from datetime import date
from decimal import Decimal

from django.test import Client, override_settings

from accounting.models import Transaction
from blog.models import Driver
from fleet.fuel import economy_for, handle_driver_message, match_bank_transactions
from fleet.models import FuelLog

BOT = dict(TELEGRAM_DRIVER_BOT_TOKEN='tok', TELEGRAM_DRIVER_BOT_USERNAME='EasyGoDriverBot',
           TELEGRAM_DRIVER_WEBHOOK_SECRET='s3cret')


class FuelBase(TestCase):
    def setUp(self):
        self.driver = Driver.objects.create(driver_name='Sung', driver_contact='0400111222',
                                            telegram_chat_id='777')
        self.vehicle = Vehicle.objects.create(make_model='Toyota Hiace', plate_number='DR15JU',
                                              assigned_driver=self.driver, odometer_km=653670,
                                              next_service_km=674000)

    def send(self, text):
        return handle_driver_message(self.driver, text)


class FuelMessageTests(FuelBase):
    def test_real_nov_fills_give_10_3_km_per_l(self):
        first = self.send('672612 50.1 132.98')
        self.assertIn('Economy will show from the next full tank', first)
        reply = self.send('673156 52.83 136.78 BP Forestville')
        self.assertIn('544 km / 52.83 L', reply)
        self.assertIn('10.3 km/L', reply)
        self.assertIn('9.7 L/100km', reply)
        self.assertIn('$2.589/L', reply)
        self.assertIn('$0.25/km', reply)
        self.assertIn('Next service in 844 km', reply)
        log = FuelLog.objects.get(odometer_km=673156)
        self.assertEqual(log.price_per_litre, Decimal('2.589'))
        self.assertEqual(log.km_per_l, Decimal('10.3'))
        self.assertEqual(log.cost_per_km, Decimal('0.25'))
        self.assertEqual(log.distance_km, 544)
        first_log = FuelLog.objects.get(odometer_km=672612)
        self.assertEqual(first_log.price_per_litre, Decimal('2.654'))
        self.assertIsNone(first_log.km_per_l)    # 직전 가득 기록이 없어 구간 없음
        self.assertIsNone(first_log.cost_per_km)
        self.assertEqual(log.notes, 'BP Forestville')
        self.assertEqual(log.driver, self.driver)
        self.assertEqual(log.source, FuelLog.SOURCE_TELEGRAM)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.odometer_km, 673156)

    def test_partial_fill_counts_toward_next_full(self):
        self.vehicle.odometer_km = None
        self.vehicle.save()
        self.send('10000 50 130')
        self.assertIn('Partial fill', self.send('p 10200 20 52'))
        self.send('10500 30 78')
        eco = economy_for(FuelLog.objects.get(odometer_km=10500))
        self.assertEqual(eco['distance_km'], 500)
        self.assertEqual(eco['litres'], Decimal('50.00'))
        self.assertEqual(eco['km_per_l'], Decimal('10.0'))
        stored = FuelLog.objects.get(odometer_km=10500)
        self.assertEqual(stored.km_per_l, Decimal('10.0'))
        self.assertEqual(stored.cost_per_km, Decimal('0.26'))   # (52+78)/500
        self.assertIsNone(FuelLog.objects.get(odometer_km=10200).km_per_l)  # 가득 아님

    def test_undo_middle_partial_recomputes_next_full(self):
        self.vehicle.odometer_km = None
        self.vehicle.save()
        self.send('10000 50 130')
        self.send('p 10200 20 52')
        self.send('10500 30 78')
        self.send('undo')          # 10500 삭제
        self.send('undo')          # 10200 삭제
        self.send('10500 30 78')
        self.assertEqual(FuelLog.objects.get(odometer_km=10500).km_per_l, Decimal('16.7'))  # 500/30

    def test_comma_odometer_and_dollar_sign(self):
        self.send('672,612 50.1 $132.98')
        self.assertTrue(FuelLog.objects.filter(odometer_km=672612, amount=Decimal('132.98')).exists())

    def test_rejects_odometer_not_increasing(self):
        self.send('672612 50.1 132.98')
        self.assertIn('not more than the last', self.send('672600 40 100'))
        self.assertEqual(FuelLog.objects.count(), 1)

    def test_rejects_big_jump_and_below_vehicle_odometer(self):
        self.assertIn('less than the vehicle', self.send('600000 50 130'))
        self.send('672612 50.1 132.98')
        self.assertIn('too far', self.send('680000 50 130'))
        self.assertEqual(FuelLog.objects.count(), 1)

    def test_rejects_swapped_order_by_price_per_litre(self):
        # 리터와 금액을 바꿔 보낸 경우: $50.1 / 132.98L = $0.38/L
        self.assertIn('Not saved', self.send('672612 132.98 50.1'))
        self.assertFalse(FuelLog.objects.exists())

    def test_undo_deletes_and_restores_odometer(self):
        self.send('672612 50.1 132.98')
        self.send('673156 52.83 136.78')
        self.assertIn('Deleted', self.send('undo'))
        self.assertFalse(FuelLog.objects.filter(odometer_km=673156).exists())
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.odometer_km, 672612)
        self.assertIn('Deleted', self.send('취소'))
        self.assertIn('Nothing to undo', self.send('undo'))

    def test_no_vehicle_assigned(self):
        self.vehicle.assigned_driver = None
        self.vehicle.save()
        self.assertIn('No vehicle is assigned', self.send('672612 50.1 132.98'))
        self.assertFalse(FuelLog.objects.exists())


class FuelBankMatchTests(FuelBase):
    def tx(self, day, amount, category='fuel'):
        return Transaction.objects.create(date=day, direction='expense', description='BP FORESTVILLE',
                                          gross_amount=Decimal(amount), category=category, source='bank')

    def log(self, day, amount, odo):
        return FuelLog.objects.create(vehicle=self.vehicle, date=day, odometer_km=odo,
                                      litres=Decimal('50'), amount=Decimal(amount))

    def test_matches_same_amount_within_window(self):
        log = self.log(date(2026, 11, 24), '132.98', 672612)
        self.tx(date(2026, 11, 23), '132.98')            # 주유 전 → 아님
        good = self.tx(date(2026, 11, 28), '132.98')
        self.tx(date(2026, 11, 28), '132.98', category='tolls')
        self.assertEqual(match_bank_transactions([log]), 1)
        log.refresh_from_db()
        self.assertEqual(log.bank_transaction, good)

    def test_one_transaction_links_only_one_log(self):
        a = self.log(date(2026, 11, 24), '100.00', 1000)
        b = self.log(date(2026, 11, 25), '100.00', 1500)
        self.tx(date(2026, 11, 27), '100.00')
        self.assertEqual(match_bank_transactions([a, b]), 1)
        self.assertEqual(FuelLog.objects.filter(bank_transaction__isnull=False).count(), 1)

    def test_outside_window_not_matched(self):
        log = self.log(date(2026, 11, 1), '90.00', 1000)
        self.tx(date(2026, 11, 20), '90.00')
        self.assertEqual(match_bank_transactions([log]), 0)


@override_settings(**BOT)
@patch('utils.telegram_driver.send_message')
class FuelWebhookTests(FuelBase):
    def post(self, chat_id, text):
        update = {'message': {'chat': {'id': int(chat_id), 'type': 'private'}, 'text': text}}
        return Client().post('/webhook/telegram/driver/', data=_json.dumps(update),
                             content_type='application/json',
                             HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN='s3cret', secure=True)

    def test_linked_driver_logs_fuel(self, send):
        self.assertEqual(self.post('777', '672612 50.1 132.98').status_code, 200)
        self.assertTrue(FuelLog.objects.filter(odometer_km=672612).exists())
        self.assertIn('Saved', send.call_args[0][1])

    def test_unlinked_chat_cannot_log(self, send):
        self.post('999', '672612 50.1 132.98')
        self.assertFalse(FuelLog.objects.exists())
        self.assertIn('Connect Telegram', send.call_args[0][1])

    def test_other_text_unchanged(self, send):
        self.post('777', 'hello')
        self.assertFalse(FuelLog.objects.exists())
        self.assertIn('Connect Telegram', send.call_args[0][1])


class FuelAdminTests(FuelBase):
    def test_changelist_and_vehicle_pages_render(self):
        from django.contrib.auth.models import User
        self.send('672612 50.1 132.98')
        self.send('673156 52.83 136.78')
        admin = User.objects.create_superuser('admin', 'a@example.com', 'pw')
        c = Client()
        c.force_login(admin)
        from django.urls import reverse
        r = c.get(reverse('admin:fleet_fuellog_changelist'), secure=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '10.3')
        html = r.content.decode()
        headers = re.findall(r'<th class="[^"]*column-(\w+)[^"]*" scope="col"', html)
        self.assertEqual(headers, ['date', 'distance_col', 'odometer_col', 'litres', 'amount_col',
                                   'price_col', 'km_per_l_col', 'cost_per_km_col'])
        for label in ('총Km', '>Odometer<', '>Amount<', '$/1L', 'Km/1L', '$/1km'):
            self.assertContains(r, label)
        self.assertContains(r, '<td class="field-distance_col">544</td>', html=False)
        for hidden in ('Full tank', 'Logged by', 'L/100km', 'L/1km', '>Bank<', '>Vehicle<'):
            self.assertNotContains(r, hidden)
        add = c.get(reverse('admin:fleet_fuellog_add'), secure=True)
        for hidden in ('Full tank', 'Logged by', 'Bank transaction'):
            self.assertNotContains(add, hidden)
        r = c.get(reverse('admin:fleet_vehicle_change', args=[self.vehicle.pk]), secure=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Next service due')


class FuelAdminRecomputeTests(FuelBase):
    def test_admin_delete_recomputes_following_log(self):
        from django.contrib.auth.models import User
        from django.urls import reverse
        self.vehicle.odometer_km = None
        self.vehicle.save()
        self.send('10000 50 130')
        self.send('p 10200 20 52')
        self.send('10500 30 78')
        admin_user = User.objects.create_superuser('admin2', 'b@example.com', 'pw')
        c = Client()
        c.force_login(admin_user)
        partial = FuelLog.objects.get(odometer_km=10200)
        r = c.post(reverse('admin:fleet_fuellog_delete', args=[partial.pk]), {'post': 'yes'}, secure=True)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(FuelLog.objects.get(odometer_km=10500).km_per_l, Decimal('16.7'))


# ── 서비스 기록 (텔레그램 드라이버 봇) ───────────────────────────────────────
from fleet.models import ServiceItem, ServiceVisit
from fleet.service_log import parse_items


class ServiceMessageTests(FuelBase):
    def setUp(self):
        super().setUp()
        self.vehicle.odometer_km = 673156
        self.vehicle.save()

    def kinds(self, visit):
        return [i.service_type for i in visit.items.all()]

    def test_self_oil_change_sets_next_service(self):
        reply = self.send('service 674100 140 oil filter Penrite 10w40, Ryco')
        self.assertIn('Self serviced · 674,100 km · $140', reply)
        self.assertIn('• Engine oil', reply)
        self.assertIn('• Oil filter', reply)
        self.assertIn('Next service: 681,100 km', reply)
        visit = ServiceVisit.objects.get()
        self.assertTrue(visit.self_serviced)
        self.assertEqual(visit.vendor, '')
        self.assertEqual(visit.total_cost, Decimal('140'))
        self.assertEqual(visit.notes, 'oil filter Penrite 10w40, Ryco')
        self.assertEqual(visit.source, ServiceVisit.SOURCE_TELEGRAM)
        self.assertEqual(visit.driver, self.driver)
        self.assertEqual(self.kinds(visit), ['engine_oil', 'oil_filter'])
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.next_service_km, 681100)
        self.assertEqual(self.vehicle.odometer_km, 674100)

    def test_known_workshop_without_separator(self):
        ServiceVisit.objects.create(vehicle=self.vehicle, service_date=date(2026, 9, 9),
                                    vendor='Ultra Tune Artarmon')
        reply = self.send('Service 674000 503 @Ultra Tune Artarmon coolant leak fixed, not genuine part')
        visit = ServiceVisit.objects.filter(source=ServiceVisit.SOURCE_TELEGRAM).get()
        self.assertFalse(visit.self_serviced)
        self.assertEqual(visit.vendor, 'Ultra Tune Artarmon')
        self.assertEqual(visit.notes, 'coolant leak fixed, not genuine part')
        self.assertIn('Next service still: 674,000 km', reply)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.next_service_km, 674000)

    def test_new_workshop_name_ends_at_colon(self):
        self.send('service 673500 700 @Seven Stars: transmission oil, brake pads')
        visit = ServiceVisit.objects.get()
        self.assertEqual(visit.vendor, 'Seven Stars')
        self.assertEqual(visit.notes, 'transmission oil, brake pads')
        self.assertEqual(self.kinds(visit), ['transmission_oil', 'brake_pad'])
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.next_service_km, 674000)   # 엔진오일 아님

    def test_item_words(self):
        self.assertEqual(parse_items('air filter, tyres'), ['air_filter', 'tyre'])
        self.assertEqual(parse_items('diff oil and fuel filter'), [])
        self.assertEqual(parse_items('battery changed'), [])

    def test_undo_service_restores_vehicle(self):
        self.send('service 674100 140 oil filter')
        self.assertIn('Deleted service', self.send('undo'))
        self.assertFalse(ServiceVisit.objects.exists())
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.next_service_km, 674000)
        self.assertEqual(self.vehicle.odometer_km, 673156)

    def test_undo_takes_latest_of_fuel_and_service(self):
        self.send('service 673200 140 oil filter')
        self.send('673500 50 130')
        self.assertIn('Deleted fuel log', self.send('undo'))
        self.assertIn('Deleted service', self.send('undo'))

    def test_bad_messages_not_saved(self):
        self.assertIn('Service log', self.send('service'))
        self.assertIn('Service log', self.send('service 674100'))
        self.assertIn('far from', self.send('service 690000 140 oil'))
        self.assertFalse(ServiceVisit.objects.exists())

    def test_fuel_messages_unchanged(self):
        self.assertIn('Fuel log', self.send('fuel'))
        self.assertIn('Saved', self.send('673500 50 130'))
        self.assertFalse(ServiceVisit.objects.exists())
