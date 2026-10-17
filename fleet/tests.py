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
