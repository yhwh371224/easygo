"""Accounting aggregations: P&L and GST/BAS reports.

This module is admin-only. Public views/templates must never import it.

build_pnl       — Transaction + PayrollEntry only; ORM-level aggregation.
build_sales_gst — blog.Post cash-basis GST 1A; Python-loop (CharField paid).
build_bas       — full BAS: 1A + 1B + W1/W2 + refund candidates.
"""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db.models import Sum

from .models import Transaction, PayrollEntry

ZERO = Decimal('0.00')

BRAND_ALL = 'all'
VALID_BRANDS = {BRAND_ALL, 'shuttle', 'coaches'}


def current_fy_end_year(today=None):
    """Australian FY ends 30 June. FY label = ending year.

    FY2026 = 2025-07-01 .. 2026-06-30.
    """
    today = today or date.today()
    return today.year if today.month < 7 else today.year + 1


def fy_range(fy_end_year):
    """Return (start, end) dates for the financial year ending in fy_end_year."""
    return date(fy_end_year - 1, 7, 1), date(fy_end_year, 6, 30)


def _sum(qs, field):
    return qs.aggregate(total=Sum(field))['total'] or ZERO


_ELEVEN = Decimal('11')
_CENT = Decimal('0.01')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_decimal_safe(value):
    """Convert a dirty CharField money value to Decimal, or Decimal('0').

    Handles: None, '', 'TBA', '$180', '1,500', '180 inc GST', floats.
    Never raises.
    """
    if value is None:
        return ZERO
    s = str(value).strip()
    if not s or s.upper() == 'TBA':
        return ZERO
    s = s.lstrip('$').replace(',', '').strip()
    try:
        return Decimal(s)
    except InvalidOperation:
        try:
            return Decimal(str(float(s)))
        except (ValueError, TypeError, InvalidOperation):
            return ZERO


# ---------------------------------------------------------------------------
# Sales GST (1A) — cash basis, Post-based
# ---------------------------------------------------------------------------

def build_sales_gst(year, quarter):
    """Return cash-basis GST collected (1A) for the given calendar quarter.

    Source: blog.Post.paid (CharField). GST registration date filter is
    applied from accounting.conf.GST_REGISTRATION_DATE.

    All posts in scope are treated as taxable supplies (GST = paid ÷ 11).
    The caller is responsible for ensuring year/quarter fall after the
    registration date; posts before that date are excluded automatically.

    Returns a dict with:
        year, quarter, gst_registration_date,
        total_paid, total_gst_1a,
        cash_paid,   cash_gst,
        online_paid, online_gst,
        post_count
    """
    from blog.models import Post
    from .conf import GST_REGISTRATION_DATE

    posts = (
        Post.objects
        .filter(
            pickup_date__isnull=False,
            pickup_date__year=year,
            pickup_date__quarter=quarter,
            pickup_date__gte=GST_REGISTRATION_DATE,
            cancelled=False,
            driver_collected_cash=False,
        )
        .exclude(paid__isnull=True)
        .exclude(paid='')
        .exclude(paid='TBA')
        .only('paid', 'cash')
    )

    total_paid = ZERO
    total_gst  = ZERO
    cash_paid  = ZERO
    cash_gst   = ZERO
    online_paid = ZERO
    online_gst  = ZERO
    count = 0

    for post in posts:
        paid = to_decimal_safe(post.paid)
        if paid <= ZERO:
            continue
        gst = (paid / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP)
        total_paid += paid
        total_gst  += gst
        count += 1
        if post.cash:
            cash_paid += paid
            cash_gst  += gst
        else:
            online_paid += paid
            online_gst  += gst

    return {
        'year': year,
        'quarter': quarter,
        'gst_registration_date': GST_REGISTRATION_DATE,
        'total_paid': total_paid,
        'total_gst_1a': total_gst,
        'cash_paid': cash_paid,
        'cash_gst': cash_gst,
        'online_paid': online_paid,
        'online_gst': online_gst,
        'post_count': count,
    }


# ---------------------------------------------------------------------------
# BAS — quarter helpers + full aggregation
# ---------------------------------------------------------------------------

# ATO BAS quarters (Australian FY).  Value = (label, used in UI dropdowns).
QUARTER_LABELS = {
    1: 'Q1 Jul–Sep',
    2: 'Q2 Oct–Dec',
    3: 'Q3 Jan–Mar',
    4: 'Q4 Apr–Jun',
}


def fy_quarter_to_range(fy_year, fy_quarter):
    """Convert FY year + BAS quarter (1–4) to (cal_year, cal_quarter, start, end).

    Australian FY quarters:
        1 = Jul–Sep  of fy_year-1  → Django cal Q3
        2 = Oct–Dec  of fy_year-1  → Django cal Q4
        3 = Jan–Mar  of fy_year    → Django cal Q1
        4 = Apr–Jun  of fy_year    → Django cal Q2
    """
    if fy_quarter == 1:
        return fy_year - 1, 3, date(fy_year - 1, 7, 1),  date(fy_year - 1, 9, 30)
    if fy_quarter == 2:
        return fy_year - 1, 4, date(fy_year - 1, 10, 1), date(fy_year - 1, 12, 31)
    if fy_quarter == 3:
        return fy_year, 1,     date(fy_year, 1, 1),       date(fy_year, 3, 31)
    if fy_quarter == 4:
        return fy_year, 2,     date(fy_year, 4, 1),       date(fy_year, 6, 30)
    raise ValueError(f"fy_quarter must be 1–4, got {fy_quarter!r}")


def build_bas(fy_year, fy_quarter):
    """Assemble full BAS data for one Australian FY quarter.

    1A  — Post.paid cash-basis GST (via build_sales_gst).
    1B  — Transaction expense rows with gst_code='gst'; uses stored gst_amount
          when > 0, else falls back to gross_amount ÷ 11.
    W1  — PayrollEntry.gross_pay total for the quarter.
    W2  — PayrollEntry.paygw_withheld total.
    net_gst — 1A − 1B.

    refund_candidates — NOT subtracted from 1A; shown for manual review only:
        (a) Cancelled Post rows with a paid amount in the quarter.
        (b) Negative-amount PaypalPayment / StripePayment rows in the quarter.
    """
    from blog.models import Post, PaypalPayment, StripePayment

    cal_year, cal_quarter, start, end = fy_quarter_to_range(fy_year, fy_quarter)

    # --- 1A ---
    sales = build_sales_gst(cal_year, cal_quarter)
    gst_1a = sales['total_gst_1a']

    # --- 1B ---
    gst_1b = ZERO
    for tx in Transaction.objects.filter(
        date__gte=start, date__lte=end,
        direction='expense', gst_code='gst',
    ):
        if tx.gst_amount > ZERO:
            gst_1b += tx.gst_amount
        else:
            gst_1b += (tx.gross_amount / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP)

    # --- W1 / W2 ---
    payroll = PayrollEntry.objects.filter(
        pay_date__gte=start, pay_date__lte=end,
    ).aggregate(w1=Sum('gross_pay'), w2=Sum('paygw_withheld'))
    w1 = payroll['w1'] or ZERO
    w2 = payroll['w2'] or ZERO

    # --- Refund candidates (display only) ---
    refund_candidates = []

    # (a) cancelled Post with a recorded paid amount
    for post in (
        Post.objects
        .filter(
            pickup_date__isnull=False,
            pickup_date__year=cal_year,
            pickup_date__quarter=cal_quarter,
            cancelled=True,
        )
        .exclude(paid__isnull=True).exclude(paid='').exclude(paid='TBA')
        .only('paid', 'name', 'email', 'pickup_date')
    ):
        paid = to_decimal_safe(post.paid)
        if paid > ZERO:
            refund_candidates.append({
                'source': 'Cancelled booking',
                'description': f"{post.name} / {post.email} — {post.pickup_date}",
                'amount': paid,
                'gst_ref': (paid / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP),
            })

    # (b) negative-amount online payment records in the quarter
    for PayModel, label in [
        (PaypalPayment, 'PayPal refund'),
        (StripePayment, 'Stripe refund'),
    ]:
        for pm in PayModel.objects.filter(
            created__date__gte=start,
            created__date__lte=end,
            amount__lt=0,
        ).only('amount', 'name', 'email'):
            amt = abs(pm.amount)
            refund_candidates.append({
                'source': label,
                'description': f"{pm.name} / {pm.email}",
                'amount': amt,
                'gst_ref': (amt / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP),
            })

    return {
        'fy_year': fy_year,
        'fy_quarter': fy_quarter,
        'fy_quarter_label': QUARTER_LABELS[fy_quarter],
        'start': start,
        'end': end,
        'sales': sales,
        'gst_1a': gst_1a,
        'gst_1b': gst_1b,
        'net_gst': gst_1a - gst_1b,
        'w1': w1,
        'w2': w2,
        'refund_candidates': refund_candidates,
    }


# ---------------------------------------------------------------------------
# P&L
# ---------------------------------------------------------------------------

def build_pnl(start, end, brand=BRAND_ALL):
    """Build the P&L summary for the given period and brand.

    brand == 'all'  -> sum across all brands; labour is included in net.
    brand == shuttle/coaches -> only that brand's Transactions; labour is
        reported as an unallocated, company-wide line and EXCLUDED from the
        brand net profit (keeps shuttle + coaches + unallocated == all).
    """
    if brand not in VALID_BRANDS:
        brand = BRAND_ALL

    tx = Transaction.objects.filter(date__gte=start, date__lte=end)
    if brand != BRAND_ALL:
        tx = tx.filter(brand=brand)

    income_total = _sum(tx.filter(direction='income'), 'gross_amount')

    expense_qs = tx.filter(direction='expense')
    expense_total = _sum(expense_qs, 'gross_amount')

    # category breakdown — grouped in the DB, not in python.
    expense_breakdown = list(
        expense_qs.values('category')
        .annotate(subtotal=Sum('gross_amount'))
        .order_by('-subtotal')
    )

    # Labour = gross_pay + super, by pay_date in the period. PayrollEntry has no
    # brand, so it is always computed company-wide regardless of brand filter.
    payroll = PayrollEntry.objects.filter(
        pay_date__gte=start, pay_date__lte=end
    ).aggregate(gross=Sum('gross_pay'), super_total=Sum('super_amount'))
    labour_total = (payroll['gross'] or ZERO) + (payroll['super_total'] or ZERO)

    is_all = brand == BRAND_ALL
    if is_all:
        # company-wide: expense + labour both reduce net
        net = income_total - (expense_total + labour_total)
        labour_in_net = True
    else:
        # brand view: labour is unallocated and excluded from brand net
        net = income_total - expense_total
        labour_in_net = False

    return {
        'start': start,
        'end': end,
        'brand': brand,
        'is_all': is_all,
        'income_total': income_total,
        'expense_total': expense_total,
        'expense_breakdown': expense_breakdown,
        'labour_total': labour_total,
        'labour_in_net': labour_in_net,
        'net': net,
        # for the "all" view, expense + labour is the total cost block
        'total_cost': (expense_total + labour_total) if is_all else expense_total,
    }
