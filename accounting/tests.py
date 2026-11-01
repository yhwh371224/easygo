import datetime
import io
import os
import tempfile
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounting.models import Transaction
from blog.models import Driver, DriverSettlement, Post
from blog.models.driver import DriverSettlementItem

HEADER = (
    'Trip/Eats ID,Transaction timestamp (UTC),Request Date (Local),'
    'Guest first name,Guest last name,Pickup Address,Transaction type,'
    'Total Taxes AUD,Transaction Amount AUD\n'
)


def uber_row(trip, charged, requested, first, last, pickup, kind, gst, amount):
    return f'{trip},{charged} 01:00:00,{requested},{first},{last},"{pickup}",{kind},{gst},{amount}\n'


class ReconcileUberTests(TestCase):

    def setUp(self):
        self.ugo = Driver.objects.create(
            driver_name='Ugo', driver_contact='0406783559',
            gst_registered=True, is_active=False,
        )
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def _post(self, name='Jason Carvalho', driver=None, price='67.55',
              pickup_date=datetime.date(2026, 10, 13), **extra):
        return Post.objects.create(
            name=name, contact='0400000000', driver=driver,
            pickup_date=pickup_date, pickup_time='05:30', driver_price=price, **extra,
        )

    def _settle(self, post, number='ALL-UGO-261015-SET-01', amount='67.55', gst='6.14'):
        settlement = DriverSettlement.objects.create(
            driver=self.ugo, settlement_number=number,
            from_date=post.pickup_date, to_date=post.pickup_date,
        )
        DriverSettlementItem.objects.create(
            settlement=settlement, post=post, amount=amount, gst_amount=gst, line_total=amount,
        )
        Transaction.objects.update_or_create(
            category='subcontract', description=number,
            defaults={
                'date': post.pickup_date, 'direction': 'expense',
                'gross_amount': amount, 'gst_code': 'gst', 'gst_amount': gst,
            },
        )
        return settlement

    def _file(self, name, text):
        path = os.path.join(self.dir.name, name)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        return path

    def _run(self, rows=None, bank=None):
        rows = rows or [uber_row(
            't1', '2026-10-12', '10/13/2026', 'Jason', 'Carvalho',
            '88 Christie St, St Leonards NSW 2065', 'Fare', '6.14', '67.55')]
        path = self._file('uber.csv', 'Company:,NEXFLOW\n\nTransactions\n' + HEADER + ''.join(rows))
        args = [path]
        if bank is not None:
            args += ['--bank', self._file('bank.csv', bank)]
        out = io.StringIO()
        call_command('reconcile_uber', *args, stdout=out)
        return out.getvalue()

    def test_settled_trip_reports_no_problems(self):
        self._settle(self._post(driver=self.ugo))
        out = self._run()
        self.assertIn('No problems found', out)
        self.assertIn('Settled   $67.55', out)

    def test_fare_and_tip_are_one_trip(self):
        self._settle(self._post(name='Amanda Clarke', driver=self.ugo, price='83.45'),
                     amount='83.45', gst='7.59')
        out = self._run([
            uber_row('t1', '2026-10-13', '10/13/2026', 'Amanda', 'Clarke', '1 A St', 'Fare', '7.13', '78.45'),
            uber_row('t1', '2026-10-13', '10/13/2026', 'Amanda', 'Clarke', '1 A St', 'Tip', '0.45', '5.00'),
        ])
        self.assertIn('1 trips', out)
        self.assertIn('No problems found', out)

    def test_unassigned_booking_is_found_by_surname(self):
        # The real miss: no driver, so nothing else in the books points at it.
        post = self._post(price='65.0')
        out = self._run()
        self.assertIn(f'Post {post.pk}', out)
        self.assertIn('matched on surname', out)
        self.assertIn('driver is none, should be Ugo', out)
        self.assertIn('driver_price is 65.0, should be 67.55', out)
        self.assertIn('not settled', out)

    def test_different_guest_is_found_by_exact_fare_on_ugo_booking(self):
        # Uber shows whoever rode; the booking can be under a colleague's name.
        post = self._post(name='Janice Quiggin', driver=self.ugo)
        self._settle(post)
        out = self._run()
        self.assertIn('No problems found', out)

    def test_address_match_when_the_name_differs(self):
        post = self._post(name='Someone Else', street='88 Christie St', price='60')
        out = self._run()
        self.assertIn(f'Post {post.pk}', out)
        self.assertIn('matched on address', out)

    def test_trip_with_no_booking(self):
        out = self._run()
        self.assertIn('no matching booking', out)

    def test_settled_without_expense_row(self):
        post = self._post(driver=self.ugo)
        self._settle(post)
        Transaction.objects.all().delete()
        out = self._run()
        self.assertIn('has no expense row', out)

    def test_one_cent_gst_rounding_is_ignored(self):
        self._settle(self._post(driver=self.ugo), gst='6.15')
        self.assertIn('No problems found', self._run())

    def test_ugo_booking_without_uber_trip_is_flagged(self):
        self._settle(self._post(driver=self.ugo))
        orphan = self._post(name='Other Person', driver=self.ugo, price='50')
        out = self._run()
        self.assertIn(f'Post {orphan.pk}', out)
        self.assertIn('assigned to Ugo, no Uber trip', out)

    def test_bank_rows_match_and_overlap_is_deduped(self):
        self._settle(self._post(driver=self.ugo))
        row = ('15/10/2026,"-67.55","UBER *BUSINESS TRIP HELP. Sydney AU Card xx9565 '
               'Value Date: 13/10/2026","+4655.76"\n')
        self.assertIn('No problems found', self._run(bank=row + row))

    def test_recent_charge_missing_from_bank_is_only_pending(self):
        self._settle(self._post(driver=self.ugo))
        bank = '28/10/2026,"-30.91","ANTHROPIC","+1.00"\n'
        out = self._run([uber_row(
            't1', '2026-10-26', '10/13/2026', 'Jason', 'Carvalho', '1 A St', 'Fare', '6.14', '67.55',
        )], bank=bank)
        self.assertIn('No problems found', out)
        self.assertIn('Not in the bank yet', out)

    def test_old_charge_missing_from_bank_is_a_problem(self):
        self._settle(self._post(driver=self.ugo))
        out = self._run(bank='30/10/2026,"-30.91","ANTHROPIC","+1.00"\n')
        self.assertIn('charged by Uber, not in the bank', out)

    def test_bank_row_missing_from_uber_is_a_problem(self):
        self._settle(self._post(driver=self.ugo))
        bank = ('15/10/2026,"-67.55","UBER *BUSINESS TRIP Value Date: 13/10/2026","+1"\n'
                '15/10/2026,"-9.99","UBER *BUSINESS TRIP Value Date: 13/10/2026","+1"\n')
        self.assertIn('in the bank, not in the Uber CSV', self._run(bank=bank))

    def test_bank_rows_outside_the_csv_period_are_ignored(self):
        self._settle(self._post(driver=self.ugo))
        bank = ('15/10/2026,"-67.55","UBER *BUSINESS TRIP Value Date: 13/10/2026","+1"\n'
                '25/08/2026,"-6.65","UBER *BUSINESS TRIP Value Date: 20/08/2026","+1"\n')
        self.assertIn('No problems found', self._run(bank=bank))

    def test_rejects_a_file_that_is_not_an_uber_csv(self):
        path = self._file('other.csv', 'a,b,c\n')
        with self.assertRaises(CommandError):
            call_command('reconcile_uber', path, stdout=io.StringIO())
