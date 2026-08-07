"""
One-off correction for PayPal fee Transaction rows recorded before the
_PAYPAL_FEE_HAS_GST fix in basecamp.modules.payment_utils (2026-08-07).

PayPal AU fees are GST-inclusive, same as Stripe, but _record_paypal_fee used
to hardcode gst_code='no_gst' / gst_amount=0. This command finds existing
PayPal payment_fee rows (individual or monthly-compacted) still marked
no_gst and corrects them to gst_code='gst' with gst_amount = gross_amount / 11.

Only rows on/after the GST registration date matter (no ITC can be claimed
before registration), so --since defaults to that date.

Safety:
- Read-only by default; pass --apply to write changes.
- Only touches source='paypal', category='payment_fee', gst_code='no_gst'.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError

from accounting.models import Transaction

_CENT = Decimal('0.01')
_ELEVEN = Decimal('11')

DEFAULT_SINCE = date(2026, 7, 1)  # ATO-confirmed GST registration date


class Command(BaseCommand):
    help = (
        "Correct PayPal payment_fee rows wrongly recorded as no_gst back to "
        "gst_code='gst' with gst_amount = gross_amount / 11."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--since', help=f"YYYY-MM-DD, default {DEFAULT_SINCE:%Y-%m-%d} (GST registration date).")
        parser.add_argument(
            '--apply', action='store_true',
            help="Actually write the changes. Without this flag, only reports what would change.")

    def handle(self, *args, **opts):
        if opts['since']:
            try:
                since = date.fromisoformat(opts['since'])
            except ValueError:
                raise CommandError("--since must be YYYY-MM-DD")
        else:
            since = DEFAULT_SINCE

        qs = Transaction.objects.filter(
            source='paypal',
            category='payment_fee',
            gst_code='no_gst',
            date__gte=since,
        ).order_by('date')

        count = qs.count()
        if count == 0:
            self.stdout.write(f"No no_gst PayPal fee rows on/after {since:%Y-%m-%d}.")
            return

        total_gst = Decimal('0')
        for t in qs:
            gst = (t.gross_amount / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP)
            total_gst += gst
            self.stdout.write(
                f"{t.date} {t.description[:60]:60s} gross={t.gross_amount:>8} "
                f"gst_amount 0 -> {gst} ({'APPLYING' if opts['apply'] else 'DRY RUN'})"
            )
            if opts['apply']:
                t.gst_code = 'gst'
                t.gst_amount = gst
                t.save(update_fields=['gst_code', 'gst_amount'])

        self.stdout.write(self.style.SUCCESS(
            f"{'Updated' if opts['apply'] else 'Would update'} {count} row(s), "
            f"total additional GST credit (1B): {total_gst}"
        ))
        if not opts['apply']:
            self.stdout.write("Re-run with --apply to write these changes.")
