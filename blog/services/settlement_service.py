from decimal import Decimal
from django.core.exceptions import ValidationError
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
            status='draft',
        )

        # 3) items 생성 + 계산
        total = Decimal('0')
        cash_total = Decimal('0')
        paid_total = Decimal('0')
        gst_total = Decimal('0')

        seq = 1

        for post in posts:
            amount = Decimal(str(post.price))

            # GST is determined by the driver's registration status, NOT by ABN —
            # an ABN holder may still be unregistered for GST. Only registered
            # drivers' settlements carry a GST component (gross ÷ 11).
            if driver.gst_registered:
                gst_amount = (amount / Decimal('11')).quantize(Decimal('0.01'))
            else:
                gst_amount = Decimal('0')

            line_total = amount + gst_amount

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

        # 4) totals 업데이트
        settlement.total_amount = total
        settlement.cash_total = cash_total
        settlement.paid_total = paid_total
        settlement.gst_total = gst_total
        settlement.save()

        return settlement


@transaction.atomic
def lock_settlement(settlement, user):
    """
    Transition settlement from draft -> locked.

    Recalculates totals from items, freezes amounts, ensures settlement_number
    and rcti_number are set, then sets status='locked' and settled_by=user.
    Raises ValidationError if settlement is not in 'draft' status.
    """
    if settlement.status != 'draft':
        raise ValidationError(
            f"Cannot lock '{settlement.settlement_number}': "
            f"expected 'draft', got '{settlement.status}'."
        )
    if not settlement.settlement_number:
        raise ValidationError("settlement_number must be set before locking.")

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
    settlement.status = 'locked'
    settlement.settled_by = user
    settlement.save()


@transaction.atomic
def mark_paid(settlement, user, payment_method, paid_at):
    """
    Transition settlement from locked -> paid.

    Sets status='paid', payment_method, paid_at, and settled_by=user.
    Raises ValidationError if settlement is not in 'locked' status.
    """
    if settlement.status != 'locked':
        raise ValidationError(
            f"Cannot mark '{settlement.settlement_number}' as paid: "
            f"expected 'locked', got '{settlement.status}'."
        )
    settlement.status = 'paid'
    settlement.payment_method = payment_method
    settlement.paid_at = paid_at
    settlement.settled_by = user
    settlement.save()

    _record_settlement_expense(settlement)


def _record_settlement_expense(settlement):
    """Create the BAS 1B expense Transaction for a paid settlement.

    Records the subcontractor payment so it flows into the BAS report. GST is
    only claimable when the driver is registered for GST — registered drivers
    get gst_code='gst' with the stored gst_total; unregistered drivers still
    have the expense recorded but with gst_code='no_gst' and zero GST.

    Idempotent: guarded on (category='subcontract', description=settlement_number)
    so repeated mark_paid calls never create duplicate expense rows.
    """
    from accounting.models import Transaction

    driver = settlement.driver
    description = settlement.settlement_number

    # Duplicate guard — one expense row per settlement
    if Transaction.objects.filter(
        category='subcontract',
        description=description,
    ).exists():
        return

    if driver.gst_registered:
        gst_code = 'gst'
        gst_amount = settlement.gst_total
    else:
        gst_code = 'no_gst'
        gst_amount = Decimal('0')

    tx_date = settlement.paid_at.date() if settlement.paid_at else timezone.now().date()

    Transaction.objects.create(
        date=tx_date,
        direction='expense',
        brand='shuttle',
        description=description,
        gross_amount=settlement.paid_total,
        gst_code=gst_code,
        gst_amount=gst_amount,
        category='subcontract',
        source='bank',
        counterparty=driver.driver_name or '',
    )