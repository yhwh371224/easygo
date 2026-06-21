"""
Import a CommBank (NetBank) CSV export into accounting.Transaction.

CommBank CSV format (NO header row), 4 columns:
    Date, Amount, Description, Balance
"""

import csv
import hashlib
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction

from accounting.models import Transaction
from accounting import conf


class Command(BaseCommand):
    help = "Import a CommBank CSV export into accounting.Transaction (expenses only)."

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help="Path to the CommBank CSV export.")
        parser.add_argument(
            '--brand', default='shuttle', choices=['shuttle', 'coaches'],
            help="Brand to tag imported rows with (default: shuttle).",
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Parse and report what WOULD happen, without writing anything.",
        )

    @staticmethod
    def _row_hash(date_str, amount_str, description, balance_str):
        raw = f"{date_str}|{amount_str}|{description}|{balance_str}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @staticmethod
    def _contains_any(haystack_upper, needles):
        return any(n.upper() in haystack_upper for n in needles)

    # Compiled once: secondary name safety-net patterns (case-insensitive).
    _DRIVER_NAME_REGEXES = [
        re.compile(p, re.IGNORECASE) for p in conf.DRIVER_SKIP_NAME_PATTERNS
    ]
    # Mansoor's PayID number, reduced to bare digits for substring matching.
    _MANSOOR_PAYID_DIGITS = re.sub(r'\D', '', conf.MANSOOR_PAYID)

    def _is_driver_payment(self, description, desc_upper):
        """True if this row looks like a driver/subcontractor payout.

        PRIMARY: Mansoor's PayID mobile number. Strip every non-digit from the
        description and test the bare 9-digit number as a substring — this
        tolerates +61 / leading 0 / spaces / hyphens and survives PayID
        display-name changes (e.g. "Paid to M JADOON +61-425455302").
        SECONDARY: a name pattern matches — backstop for rows that carry the
        name but not the number.
        """
        if self._MANSOOR_PAYID_DIGITS:
            desc_digits = re.sub(r'\D', '', description)
            if self._MANSOOR_PAYID_DIGITS in desc_digits:
                return True
        return any(rx.search(desc_upper) for rx in self._DRIVER_NAME_REGEXES)

    def _estimate_gst(self, description_upper, gross):
        for keywords, code in conf.GST_KEYWORD_RULES:
            if self._contains_any(description_upper, keywords):
                if code == 'gst':
                    gst_amt = (gross / Decimal('11')).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP)
                    return 'gst', gst_amt, True
                return code, Decimal('0.00'), True
        return 'no_gst', Decimal('0.00'), True

    def _category(self, description_upper):
        for keywords, cat in conf.CATEGORY_KEYWORD_RULES:
            if self._contains_any(description_upper, keywords):
                return cat
        return 'uncategorised'

    def handle(self, *args, **opts):
        path = opts['csv_path']
        brand = opts['brand']
        dry_run = opts['dry_run']

        try:
            fh = open(path, newline='', encoding='utf-8-sig')
        except OSError as e:
            raise CommandError(f"Could not open {path}: {e}")

        created = skipped_income = skipped_driver = skipped_transfer = 0
        skipped_dup = errors = held_for_review = 0
        to_create = []

        with fh:
            reader = csv.reader(fh)
            for lineno, row in enumerate(reader, start=1):
                if not row or len(row) < 4:
                    continue
                date_str, amount_str, description, balance_str = (
                    row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip())

                try:
                    amount = Decimal(amount_str.replace(',', ''))
                except Exception:
                    self.stderr.write(f"  line {lineno}: bad amount {amount_str!r} — skipped")
                    errors += 1
                    continue

                if amount >= 0:
                    skipped_income += 1
                    continue

                desc_upper = description.upper()

                if self._contains_any(desc_upper, conf.INTERNAL_TRANSFER_MARKERS):
                    skipped_transfer += 1
                    continue

                if self._is_driver_payment(description, desc_upper):
                    skipped_driver += 1
                    continue

                try:
                    tx_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                except ValueError:
                    self.stderr.write(f"  line {lineno}: bad date {date_str!r} — skipped")
                    errors += 1
                    continue

                gross = abs(amount)
                row_hash = self._row_hash(date_str, amount_str, description, balance_str)

                if Transaction.objects.filter(import_hash=row_hash).exists():
                    skipped_dup += 1
                    continue

                if tx_date >= conf.GST_REGISTRATION_DATE:
                    gst_code, gst_amount, auto_flag = self._estimate_gst(desc_upper, gross)
                else:
                    gst_code, gst_amount, auto_flag = 'no_gst', Decimal('0.00'), False

                # Large withdrawals are held for human triage: imported but kept
                # out of BAS 1B / P&L totals (needs_review) until approved or
                # excluded in the admin.
                needs_review = gross >= conf.REVIEW_THRESHOLD
                if needs_review:
                    held_for_review += 1

                to_create.append(Transaction(
                    date=tx_date,
                    direction='expense',
                    brand=brand,
                    description=description[:255],
                    gross_amount=gross,
                    gst_code=gst_code,
                    gst_amount=gst_amount,
                    category=self._category(desc_upper),
                    source='bank',
                    counterparty='',
                    notes='',
                    import_hash=row_hash,
                    gst_auto_estimated=auto_flag,
                    needs_review=needs_review,
                ))
                created += 1

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Bank CSV import summary"))
        self.stdout.write(f"  To import (expenses):        {created}")
        self.stdout.write(f"    of which held (needs_review): {held_for_review}")
        self.stdout.write(f"  Skipped — income rows:       {skipped_income}")
        self.stdout.write(f"  Skipped — driver payments:   {skipped_driver}")
        self.stdout.write(f"  Skipped — internal transfer: {skipped_transfer}")
        self.stdout.write(f"  Skipped — duplicates:        {skipped_dup}")
        self.stdout.write(f"  Errors (bad row):            {errors}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN — nothing written."))
            for t in to_create[:20]:
                if t.needs_review:
                    flag = " [NEEDS_REVIEW ≥ threshold]"
                elif t.gst_auto_estimated and t.gst_code == 'no_gst':
                    flag = " [gst review]"
                else:
                    flag = ""
                self.stdout.write(
                    f"    {t.date}  -{t.gross_amount:>8}  {t.gst_code:8} "
                    f"{t.category:20} {t.description[:40]}{flag}")
            if len(to_create) > 20:
                self.stdout.write(f"    ... and {len(to_create) - 20} more")
            return

        if to_create:
            with db_transaction.atomic():
                Transaction.objects.bulk_create(to_create)
            self.stdout.write(self.style.SUCCESS(f"\nImported {created} transactions."))
        else:
            self.stdout.write("\nNothing new to import.")

        review_count = sum(
            1 for t in to_create
            if t.gst_auto_estimated and t.gst_code == 'no_gst')
        if review_count:
            self.stdout.write(self.style.WARNING(
                f"{review_count} row(s) need GST review "
                f"(imported as no_gst, gst_auto_estimated=True)."))
