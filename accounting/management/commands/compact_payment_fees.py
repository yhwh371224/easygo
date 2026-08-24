"""
Compact individual PayPal/Stripe fee rows logged in PaymentFeeLog into one
summary Transaction row per source per month, so the accounting Transaction
list only ever sees one line for PayPal/Stripe fees each month instead of
dozens of $2-15 fee rows.

Intended to run on the 7th of each month, for the PREVIOUS calendar month —
by then any pending Celery retries (Stripe, up to ~6.5 min after checkout —
see basecamp.tasks.record_stripe_fee_task) or delayed PayPal IPNs have long
settled, so nothing still in flight gets swept into the summary and lost.

Safety:
- Only merges rows that share the same gst_code/direction/brand within the
  month; if a source's rows are inconsistent, that source is left untouched
  and reported so it can be checked by hand.
- The summary row's gross_amount/gst_amount are the exact sum of the rows it
  replaces, so BAS 1B / P&L totals for the month are unchanged.
- Every original description is kept in the summary row's notes field, so
  the per-payment (txn_id / payment_intent_id) audit trail isn't lost.
- Idempotent: PaymentFeeLog only ever holds raw (never summarized) rows, and
  merged rows are deleted from it once folded into the Transaction summary,
  so re-running for an already-compacted month just finds nothing left and
  is a harmless no-op.
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from django.db.models import Sum

from accounting.models import PaymentFeeLog, Transaction

SOURCE_LABELS = {'paypal': 'PayPal', 'stripe': 'Stripe'}


def _previous_month(today):
    first_of_this_month = today.replace(day=1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    return last_of_prev_month.year, last_of_prev_month.month


class Command(BaseCommand):
    help = ("Compact last month's individual PayPal/Stripe payment_fee rows "
            "into one summary row per source. Run on the 7th of the month.")

    def add_arguments(self, parser):
        parser.add_argument(
            '--month', help="Target month as YYYY-MM (default: previous calendar month).")
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Report what WOULD happen, without writing/deleting anything.")

    def handle(self, *args, **opts):
        if opts['month']:
            try:
                year_str, month_str = opts['month'].split('-')
                year, month = int(year_str), int(month_str)
            except ValueError:
                raise CommandError("--month must be YYYY-MM")
        else:
            year, month = _previous_month(date.today())

        month_start = date(year, month, 1)
        month_end = date(year, month, calendar.monthrange(year, month)[1])

        for source in ('paypal', 'stripe'):
            self._compact_source(source, month_start, month_end, opts['dry_run'])

    def _compact_source(self, source, month_start, month_end, dry_run):
        label = SOURCE_LABELS[source]
        summary_prefix = f"{label} fees — "

        qs = PaymentFeeLog.objects.filter(
            source=source,
            date__gte=month_start,
            date__lte=month_end,
        )

        count = qs.count()
        if count == 0:
            self.stdout.write(f"{source}: no rows for {month_start:%Y-%m}, skipping.")
            return

        gst_codes = set(qs.values_list('gst_code', flat=True).distinct())
        directions = set(qs.values_list('direction', flat=True).distinct())
        brands = set(qs.values_list('brand', flat=True).distinct())
        if len(gst_codes) > 1 or len(directions) > 1 or len(brands) > 1:
            self.stderr.write(
                f"{source}: inconsistent gst_code/direction/brand in "
                f"{month_start:%Y-%m} (gst_code={gst_codes}, direction={directions}, "
                f"brand={brands}) — refusing to merge, leaving {count} rows untouched.")
            return

        totals = qs.aggregate(gross=Sum('gross_amount'), gst=Sum('gst_amount'))
        gross = totals['gross'] or Decimal('0')
        gst = totals['gst'] or Decimal('0')
        gst_code = gst_codes.pop()
        direction = directions.pop()
        brand = brands.pop()

        descriptions = list(qs.order_by('date').values_list('description', flat=True))
        summary_description = f"{summary_prefix}{month_start:%Y-%m} ({count}건 압축)"
        notes = (
            f"Compacted {count} individual {label} fee rows for {month_start:%Y-%m}.\n"
            + "\n".join(descriptions)
        )

        self.stdout.write(
            f"{source}: {count} rows -> 1 row, gross={gross}, gst={gst} "
            f"({'DRY RUN' if dry_run else 'WRITING'})")

        if dry_run:
            return

        with db_transaction.atomic():
            Transaction.objects.create(
                date=month_end,
                direction=direction,
                brand=brand,
                description=summary_description,
                gross_amount=gross,
                gst_code=gst_code,
                gst_amount=gst,
                category='payment_fee',
                source=source,
                counterparty=label,
                notes=notes,
            )
            qs.delete()

        self.stdout.write(self.style.SUCCESS(
            f"{source}: compacted {count} rows for {month_start:%Y-%m}."))
