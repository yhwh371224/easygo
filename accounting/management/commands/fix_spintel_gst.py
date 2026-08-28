"""
One-off correction for SpinTel (mobile + internet) bank rows imported before
the SPINTEL / '617704 PAYPAL' rules were added to accounting.conf (2026-08-28).

The bill is paid through PayPal, so the bank row carries no merchant name —
only PayPal's direct-debit reference, e.g.
    Direct Debit 617704 PAYPAL AUSTRALIA 105...
With no keyword to match, import_bank_csv landed these as
gst_code='no_gst' / category='uncategorised'. They are GST-inclusive phone and
internet costs (confirmed by the owner), so this command re-files them as
gst_code='gst', gst_amount = gross_amount / 11, category='phone_internet'.

Only rows on/after the GST registration date matter (no ITC before then), so
--since defaults to that date.

Safety:
- Read-only by default; pass --apply to write changes.
- Only touches source='bank', gst_code='no_gst', not excluded, description
  matching SPINTEL or the PayPal debit reference.
- Rows already categorised as something other than 'uncategorised' or
  'phone_internet' are listed and skipped — an owner decision beats this rule.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from accounting.models import Transaction
from accounting import conf

_CENT = Decimal('0.01')
_ELEVEN = Decimal('11')

# Same markers as the conf rules, kept here so the command still finds rows if
# the conf tuples are ever reshuffled.
MARKERS = ('SPINTEL', '617704 PAYPAL')

# Categories this command is willing to overwrite.
SAFE_CATEGORIES = {'uncategorised', 'phone_internet'}


class Command(BaseCommand):
    help = (
        "Re-file SpinTel/PayPal direct-debit bank rows imported as "
        "no_gst/uncategorised into gst + phone_internet."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--since',
            help=f"YYYY-MM-DD, default {conf.GST_REGISTRATION_DATE:%Y-%m-%d} "
                 f"(GST registration date).")
        parser.add_argument(
            '--apply', action='store_true',
            help="Actually write the changes. Without this flag, only reports "
                 "what would change.")

    def handle(self, *args, **opts):
        if opts['since']:
            try:
                since = date.fromisoformat(opts['since'])
            except ValueError:
                raise CommandError("--since must be YYYY-MM-DD")
        else:
            since = conf.GST_REGISTRATION_DATE

        desc_match = Q()
        for marker in MARKERS:
            desc_match |= Q(description__icontains=marker)

        qs = Transaction.objects.filter(
            desc_match,
            source='bank',
            direction='expense',
            gst_code='no_gst',
            excluded=False,
            date__gte=since,
        ).order_by('date')

        if not qs.exists():
            self.stdout.write(
                f"No no_gst SpinTel/PayPal-debit bank rows on/after {since:%Y-%m-%d}.")
            return

        applying = opts['apply']
        total_gst = Decimal('0')
        changed = skipped = 0

        for t in qs:
            if t.category not in SAFE_CATEGORIES:
                self.stdout.write(self.style.WARNING(
                    f"{t.date} {t.description[:50]:50s} gross={t.gross_amount:>8} "
                    f"— already categorised '{t.category}', skipped"))
                skipped += 1
                continue

            gst = (t.gross_amount / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP)
            total_gst += gst
            changed += 1
            self.stdout.write(
                f"{t.date} {t.description[:50]:50s} gross={t.gross_amount:>8} "
                f"no_gst/{t.category} -> gst/{gst}/phone_internet "
                f"({'APPLYING' if applying else 'DRY RUN'})")
            if applying:
                t.gst_code = 'gst'
                t.gst_amount = gst
                t.category = 'phone_internet'
                t.gst_auto_estimated = False  # owner-confirmed, not a guess
                t.needs_review = False
                t.is_tax_deductible = True
                t.save(update_fields=[
                    'gst_code', 'gst_amount', 'category',
                    'gst_auto_estimated', 'needs_review', 'is_tax_deductible',
                ])

        self.stdout.write(self.style.SUCCESS(
            f"{'Updated' if applying else 'Would update'} {changed} row(s)"
            f"{f', skipped {skipped}' if skipped else ''}, "
            f"total additional GST credit (1B): {total_gst}"))
        if not applying:
            self.stdout.write("Re-run with --apply to write these changes.")
