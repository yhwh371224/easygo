from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from blog.models import DriverSettlement
from blog.models.driver import DriverSettlementItem
from blog.models import Post
from blog.utils.number_generate import generate_settlement_number


class SettlementService:

    @staticmethod
    @transaction.atomic
    def create_settlement(driver, from_date, to_date, user=None):
        """
        1. Post 가져오기
        2. Settlement 생성
        3. Item 생성
        4. totals 계산
        """

        # 1) posts 조회
        posts = Post.objects.filter(
            driver=driver,
            pickup_date__gte=from_date,
            pickup_date__lte=to_date,
            cancelled=False,
        ).exclude(price__isnull=True).exclude(price='')

        if not posts.exists():
            return None

        # 2) settlement 생성
        seq = DriverSettlement.objects.filter(
            driver=driver, to_date=to_date
        ).count() + 1
        settlement = DriverSettlement.objects.create(
            driver=driver,
            from_date=from_date,
            to_date=to_date,
            settlement_number=generate_settlement_number(driver, to_date, seq),
            settled_by=user,
            # One-step flow: a settlement is complete the moment it is created.
            # 'paid' keeps the driver-facing RCTI page / PDF visible and makes the
            # expense count immediately. It stays fully editable afterwards.
            status='paid',
        )

        # 3) items 생성 + 계산
        total = Decimal('0')
        cash_total = Decimal('0')
        paid_total = Decimal('0')
        gst_total = Decimal('0')

        seq = 1

        for post in posts:
            # Subcontractor payout = price − company commission (price × rate%).
            # The full price stays untouched in the DB (display-only invoice
            # principle); the commission margin is implicit in price − payout.
            amount = post.subcontractor_payout

            # GST is determined by the driver's registration status, NOT by ABN —
            # an ABN holder may still be unregistered for GST. The customer price
            # is GST-inclusive (from 2026-07-01), so subcontractor_payout is also
            # GST-inclusive. For registered drivers we only EXTRACT the embedded
            # GST (gross ÷ 11) for the RCTI/1B line — we never add it on top, or
            # the driver would be overpaid and the expense overstated.
            if driver.gst_registered:
                gst_amount = (amount / Decimal('11')).quantize(Decimal('0.01'))
            else:
                gst_amount = Decimal('0')

            line_total = amount

            DriverSettlementItem.objects.create(
                settlement=settlement,
                post=post,
                amount=amount,
                gst_amount=gst_amount,
                line_total=line_total,
                description=f"{post.pickup_date} {post.pickup_time}"
            )

            total += line_total
            gst_total += gst_amount

            if post.cash:
                cash_total += line_total
            else:
                paid_total += line_total

            seq += 1

        # 4) totals 업데이트 + 회계 비용 기록 (one-step: 생성 = 완료)
        settlement.total_amount = total
        settlement.cash_total = cash_total
        settlement.paid_total = paid_total
        settlement.gst_total = gst_total
        settlement.save()

        sync_settlement_expense(settlement)

        return settlement


def recompute_totals(settlement):
    """Re-derive the four money totals from the current line items.

    Called after a settlement is edited in the admin (items added/changed/
    removed) so the stored header totals always match the items.
    """
    total = Decimal('0')
    cash_total = Decimal('0')
    paid_total = Decimal('0')
    gst_total = Decimal('0')

    for item in settlement.items.select_related('post').all():
        total += item.line_total
        gst_total += item.gst_amount
        if item.post.cash:
            cash_total += item.line_total
        else:
            paid_total += item.line_total

    settlement.total_amount = total
    settlement.cash_total = cash_total
    settlement.paid_total = paid_total
    settlement.gst_total = gst_total
    settlement.save(update_fields=[
        'total_amount', 'cash_total', 'paid_total', 'gst_total',
    ])


@transaction.atomic
def sync_settlement_expense(settlement):
    """Create / update / remove the BAS 1B expense Transaction for a settlement.

    Idempotent upsert keyed on (category='subcontract',
    description=settlement_number) — one expense row per settlement. Safe to
    call on every create and every edit, so the books always match the
    settlement (no lock step needed).

    GST is only claimable when the driver is registered for GST — registered
    drivers get gst_code='gst' with the recomputed GST; unregistered drivers
    still have the expense recorded but with gst_code='no_gst' and zero GST.

    The expense base is recomputed from the settlement items: any post the
    driver collected cash for (post.cash) or the customer paid the driver in
    cash for (post.driver_collected_cash) never passed through the company, so
    it is excluded from both gross_amount and gst_amount. If nothing is
    claimable, any existing expense row is removed.
    """
    from accounting.models import Transaction

    driver = settlement.driver
    description = settlement.settlement_number

    expense_gross = Decimal('0')
    expense_gst   = Decimal('0')
    for item in settlement.items.select_related('post'):
        if item.post.cash or item.post.driver_collected_cash:
            continue
        expense_gross += item.line_total
        expense_gst   += item.gst_amount

    existing = Transaction.objects.filter(
        category='subcontract', description=description,
    ).first()

    # Nothing left to claim (e.g. all rides were cash, or items removed) —
    # drop any stale expense row so the books stay in sync.
    if expense_gross <= Decimal('0'):
        if existing:
            existing.delete()
        return

    if driver.gst_registered:
        gst_code, gst_amount = 'gst', expense_gst
    else:
        gst_code, gst_amount = 'no_gst', Decimal('0')

    tx_date = (settlement.settled_at.date()
               if settlement.settled_at else timezone.now().date())

    fields = dict(
        date=tx_date,
        direction='expense',
        brand='shuttle',
        gross_amount=expense_gross,
        gst_code=gst_code,
        gst_amount=gst_amount,
        source='bank',
        counterparty=driver.driver_name or '',
    )

    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
        existing.save()
    else:
        Transaction.objects.create(
            category='subcontract', description=description, **fields,
        )


def delete_settlement_expense(settlement):
    """Remove the expense Transaction tied to a settlement (on delete)."""
    from accounting.models import Transaction

    Transaction.objects.filter(
        category='subcontract', description=settlement.settlement_number,
    ).delete()