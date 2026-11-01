"""
Compare an Uber for Business transaction CSV against the books. Read-only.

Uber rides are booked as driver 'Ugo' and reach the P&L only through a
DriverSettlement, because the UBER *BUSINESS bank rows are skipped at import
(see accounting.conf.DRIVER_PAYOUT_MARKERS). A trip that never got assigned to
Ugo therefore leaves no trace in the books. This command starts from Uber's own
list so those trips show up, and prints whatever doesn't line up:

    python manage.py reconcile_uber u4b_transaction_csv.csv
    python manage.py reconcile_uber u4b_transaction_csv.csv --bank bank10.csv bank11.csv
"""

import csv
import io
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from accounting.models import Transaction
from blog.models import Post

UBER_HEADER = 'Trip/Eats ID'
BANK_MARKER = 'UBER *BUSINESS'

# Settlement GST is price/11 of the whole trip; Uber rounds fare and tip apart.
GST_TOLERANCE = Decimal('0.02')
# An Uber request can fall on the other side of midnight from the booking.
POST_DATE_WINDOW = timedelta(days=1)
# Uber's charge time vs the bank's Value Date.
BANK_DATE_WINDOW = timedelta(days=3)
# A charge this close to the end of the statement may just not have posted yet.
BANK_PENDING_WINDOW = timedelta(days=7)


def parse_uber_text(text):
    """Group the Uber CSV into trips: fare + tip rows share one Trip ID."""
    start = text.find(UBER_HEADER)
    if start < 0:
        raise CommandError(f"No '{UBER_HEADER}' header — not an Uber transaction CSV.")

    trips = {}
    for row in csv.DictReader(io.StringIO(text[start:])):
        trip_id = (row.get(UBER_HEADER) or '').strip()
        if not trip_id or row.get('Transaction Amount AUD') is None:
            continue
        try:
            amount = Decimal(row['Transaction Amount AUD'])
            gst = Decimal(row['Total Taxes AUD'])
            trip_date = datetime.strptime(row['Request Date (Local)'], '%m/%d/%Y').date()
            charged = datetime.strptime(
                row['Transaction timestamp (UTC)'][:10], '%Y-%m-%d').date()
        except (InvalidOperation, ValueError, KeyError, TypeError) as exc:
            raise CommandError(f"Unreadable Uber row for trip {trip_id}: {exc}")

        trip = trips.setdefault(trip_id, {
            'date': trip_date,
            'first_name': row.get('Guest first name', '').strip(),
            'last_name': row.get('Guest last name', '').strip(),
            'pickup': row.get('Pickup Address', ''),
            'amount': Decimal('0'),
            'gst': Decimal('0'),
            'charges': [],
        })
        trip['amount'] += amount
        trip['gst'] += gst
        trip['charges'].append({'date': charged, 'amount': amount, 'guest': (
            f"{trip['first_name']} {trip['last_name']}")})
    return list(trips.values())


def parse_bank_text(text):
    """Return the UBER *BUSINESS rows of a CommBank CSV as a set of tuples.

    A set, because consecutive statement downloads overlap. Each tuple is
    (posted date, amount as positive Decimal, value date, raw description).
    """
    rows = set()
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 3 or BANK_MARKER not in row[2].upper():
            continue
        try:
            posted = datetime.strptime(row[0], '%d/%m/%Y').date()
            amount = -Decimal(row[1])
        except (InvalidOperation, ValueError):
            continue
        found = re.search(r'Value Date: (\d{2}/\d{2}/\d{4})', row[2])
        value_date = (
            datetime.strptime(found.group(1), '%d/%m/%Y').date() if found else posted)
        rows.add((posted, amount, value_date, row[2]))
    return rows


def latest_bank_date(paths_text):
    """Last posted date across the statements, Uber rows or not."""
    latest = None
    for text in paths_text:
        for row in csv.reader(io.StringIO(text)):
            try:
                posted = datetime.strptime(row[0], '%d/%m/%Y').date()
            except (IndexError, ValueError):
                continue
            if latest is None or posted > latest:
                latest = posted
    return latest


def to_decimal(value):
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def name_matches(word, post_name):
    return len(word) >= 3 and re.search(
        r'\b' + re.escape(word) + r'\b', post_name or '', re.IGNORECASE)


def street_matches(post, pickup):
    tokens = (post.street or '').lower().split()
    return len(tokens) >= 2 and ' '.join(tokens[:2]) in pickup.lower()


def find_post(trip, used):
    """Best booking for a trip, most reliable evidence first.

    Returns (post, how). An Ugo booking at the exact fare wins over a name match
    so a customer's two bookings around the same date don't get crossed.
    """
    candidates = [
        post for post in Post.objects.filter(
            pickup_date__gte=trip['date'] - POST_DATE_WINDOW,
            pickup_date__lte=trip['date'] + POST_DATE_WINDOW,
        ).select_related('driver')
        if post.pk not in used
    ]
    candidates.sort(key=lambda post: abs(post.pickup_date - trip['date']))

    rules = [
        ('fare', lambda post: is_ugo(post) and to_decimal(post.driver_price) == trip['amount']),
        ('surname', lambda post: name_matches(trip['last_name'], post.name)),
        ('address', lambda post: street_matches(post, trip['pickup'])),
        ('first name', lambda post: name_matches(trip['first_name'], post.name)),
    ]
    for how, rule in rules:
        for post in candidates:
            if rule(post):
                return post, how
    return None, None


def is_ugo(post):
    return bool(post.driver) and (post.driver.driver_name or '').strip().lower() == 'ugo'


def check_trip(trip, post):
    """Everything wrong with one trip, and the amount the books carry for it."""
    amount = trip['amount']
    if post is None:
        return ['no matching booking'], None, None

    problems = []
    if post.cancelled:
        problems.append('booking is cancelled')
    if not is_ugo(post):
        driver = post.driver.driver_name if post.driver else 'none'
        problems.append(f'driver is {driver}, should be Ugo')
    if to_decimal(post.driver_price) != amount:
        problems.append(f'driver_price is {post.driver_price}, should be {amount}')

    items = list(post.driversettlementitem_set.select_related('settlement'))
    if not items:
        problems.append('not settled')
        return problems, None, None

    booked = sum((item.line_total for item in items), Decimal('0'))
    booked_gst = sum((item.gst_amount for item in items), Decimal('0'))
    if booked != amount:
        problems.append(f'settled {booked}, should be {amount}')
    if abs(booked_gst - trip['gst']) > GST_TOLERANCE:
        problems.append(f"settled GST {booked_gst}, Uber says {trip['gst']}")
    for item in items:
        number = item.settlement.settlement_number
        if not Transaction.objects.filter(
                category='subcontract', description=number, excluded=False).exists():
            problems.append(f'settlement {number} has no expense row')
    return problems, booked, booked_gst


def compare_bank(trips, bank_rows, latest_posted):
    """Tie each Uber charge to a bank row. Returns (problems, pending)."""
    unmatched = sorted(bank_rows, key=lambda row: row[2])
    problems, pending = [], []
    charges = [charge for trip in trips for charge in trip['charges']]

    for charge in sorted(charges, key=lambda charge: charge['date']):
        match = next((
            row for row in unmatched
            if row[1] == charge['amount']
            and abs(row[2] - charge['date']) <= BANK_DATE_WINDOW
        ), None)
        label = f"{charge['date']} ${charge['amount']} {charge['guest']}"
        if match:
            unmatched.remove(match)
        elif latest_posted and charge['date'] >= latest_posted - BANK_PENDING_WINDOW:
            pending.append(label)
        else:
            problems.append(f'{label}: charged by Uber, not in the bank')

    first = min(charge['date'] for charge in charges) - BANK_DATE_WINDOW
    last = max(charge['date'] for charge in charges) + BANK_DATE_WINDOW
    for posted, amount, value_date, _ in unmatched:
        if first <= value_date <= last:
            problems.append(f'{posted} ${amount}: in the bank, not in the Uber CSV')
    return problems, pending


class Command(BaseCommand):
    help = "Compare an Uber for Business CSV against bookings and settlements (read-only)."

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help="Path to the Uber u4b_transaction_csv file.")
        parser.add_argument(
            '--bank', nargs='*', default=[], metavar='CSV',
            help="CommBank CSV exports to compare the charges against as well.",
        )

    @staticmethod
    def _read(path):
        try:
            with open(path, encoding='utf-8-sig') as handle:
                return handle.read()
        except OSError as exc:
            raise CommandError(str(exc))

    def handle(self, *args, **options):
        uber_text = self._read(options['csv_path'])
        bank_texts = [self._read(path) for path in options['bank']]
        self.report(uber_text, bank_texts)

    def report(self, uber_text, bank_texts):
        trips = sorted(parse_uber_text(uber_text), key=lambda trip: trip['date'])
        if not trips:
            raise CommandError("No transactions in the Uber CSV.")

        used = set()
        issues = []
        booked_total = booked_gst_total = Decimal('0')
        for trip in trips:
            post, how = find_post(trip, used)
            problems, booked, booked_gst = check_trip(trip, post)
            if post:
                used.add(post.pk)
            booked_total += booked or 0
            booked_gst_total += booked_gst or 0
            if problems:
                guest = f"{trip['first_name']} {trip['last_name']}"
                where = f'Post {post.pk} ({post.name}, matched on {how})' if post else trip['pickup']
                issues.append(
                    f"{trip['date']} {guest} ${trip['amount']} — {where}: "
                    + '; '.join(problems))

        first, last = trips[0]['date'], trips[-1]['date']
        orphans = Post.objects.filter(
            driver__driver_name__iexact='ugo', cancelled=False,
            pickup_date__gte=first, pickup_date__lte=last,
        ).exclude(pk__in=used).order_by('pickup_date')
        for post in orphans:
            issues.append(
                f'{post.pickup_date} Post {post.pk} ({post.name}) ${post.driver_price}: '
                'assigned to Ugo, no Uber trip')

        uber_total = sum((trip['amount'] for trip in trips), Decimal('0'))
        uber_gst = sum((trip['gst'] for trip in trips), Decimal('0'))
        self.stdout.write(f'Uber CSV {first} ~ {last}: {len(trips)} trips')
        self.stdout.write(f'  Uber      ${uber_total}  GST ${uber_gst}')
        self.stdout.write(f'  Settled   ${booked_total}  GST ${booked_gst_total}')

        pending = []
        if bank_texts:
            bank_rows = set().union(*(parse_bank_text(text) for text in bank_texts))
            bank_issues, pending = compare_bank(trips, bank_rows, latest_bank_date(bank_texts))
            issues.extend(bank_issues)

        self.stdout.write('')
        if issues:
            self.stdout.write(self.style.WARNING(f'{len(issues)} PROBLEM(S):'))
            for issue in issues:
                self.stdout.write(f'  - {issue}')
        else:
            self.stdout.write(self.style.SUCCESS('No problems found.'))
        if pending:
            self.stdout.write('\nNot in the bank yet (too recent to call missing):')
            for label in pending:
                self.stdout.write(f'  - {label}')
