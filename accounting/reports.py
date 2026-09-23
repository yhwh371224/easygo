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


_PAYPAL_SURCHARGE_RATE = Decimal('1.03')


def paypal_surcharge_total(start, end):
    """Sum the 3% PayPal card surcharge received between start and end.

    notify_user_payment_paypal (blog/tasks.py) applies only amount ÷ 1.03 to
    Post.paid, so the surcharge never reaches the booking-based income. It is
    still taxable revenue, so it is added here from the PayPal IPN rows,
    dated by when the money moved (created).

    Refunds (negative amount) subtract their own surcharge portion, so a
    cancelled + refunded booking leaves no surcharge behind. The base portion
    of a refund is netted on the booking side via Post.refund, which
    _auto_fill_post_refund stores ex-surcharge for PayPal.

    Disputes (Reversed — the customer pulled the money back) also take the
    original payment's surcharge off, and a Canceled_Reversal puts it back.
    PayPal can send several Reversed IPNs for one payment (e.g. 2026-08-25 and
    again 2026-09-04 for the same parent_txn_id), so only the earliest row per
    parent payment and kind counts, across all periods.
    """
    from blog.models import PaypalPayment

    def surcharge_of(amount):
        # quantize the base, not the surcharge, to mirror blog/tasks.py's
        # round(amount / 1.03, 2) applied to Post.paid.
        base = (amount / _PAYPAL_SURCHARGE_RATE).quantize(_CENT, rounding=ROUND_HALF_UP)
        return amount - base

    total = ZERO
    for pm in PaypalPayment.objects.filter(
        created__date__gte=start, created__date__lte=end,
    ).exclude(amount__isnull=True).exclude(amount=0):
        kind = pm.kind
        if kind in (PaypalPayment.KIND_PAYMENT, PaypalPayment.KIND_REFUND):
            total += surcharge_of(pm.amount)   # negative for a refund
            continue

        if not pm.parent_txn_id:
            continue
        siblings = [
            o for o in PaypalPayment.objects.filter(parent_txn_id=pm.parent_txn_id)
            .exclude(amount=0).order_by('created', 'pk')
            if o.kind == kind
        ]
        if not siblings or siblings[0].pk != pm.pk:
            continue
        parent = PaypalPayment.objects.filter(txn_id=pm.parent_txn_id).first()
        amount = abs(parent.amount) if parent and parent.amount else abs(pm.amount)
        if kind == PaypalPayment.KIND_DISPUTE:
            total -= surcharge_of(amount)
        elif kind == PaypalPayment.KIND_DISPUTE_RESOLVED:
            total += surcharge_of(amount)
    return total


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
        .only('paid', 'cash', 'refund')
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
        # Net any customer refund off the sale (cash-basis): the company only
        # collected paid − refund, so 1A GST is charged on the net. Refund is
        # netted in the pickup_date quarter (we have no separate refund date).
        refund = post.refund or ZERO
        paid = paid - refund
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

    # PayPal 3% surcharge (not in Post.paid) — online, dated by receipt.
    q_start = date(year, 3 * quarter - 2, 1)
    q_end = date(year, 3 * quarter, 31 if quarter in (1, 4) else 30)
    surcharge = paypal_surcharge_total(max(q_start, GST_REGISTRATION_DATE), q_end)
    surcharge_gst = (surcharge / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP)
    total_paid  += surcharge
    total_gst   += surcharge_gst
    online_paid += surcharge
    online_gst  += surcharge_gst

    return {
        'year': year,
        'quarter': quarter,
        'gst_registration_date': GST_REGISTRATION_DATE,
        'paypal_surcharge': surcharge,
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


_MATCH_TOLERANCE = Decimal('0.02')


def _near(a, b):
    return abs(a - b) <= _MATCH_TOLERANCE


def _refund_base(pm, amt):
    """Refund amount on the same basis as Post.paid: PayPal ex 3% surcharge."""
    from blog.models import PaypalPayment
    if isinstance(pm, PaypalPayment):
        return (amt / _PAYPAL_SURCHARGE_RATE).quantize(_CENT, rounding=ROUND_HALF_UP)
    return amt


def _payer_refunds(post):
    """Refund rows (PayPal kind=refund, negative Stripe) from this booking's payer."""
    from django.db.models import Q
    from blog.models import PaypalPayment, StripePayment

    q = Q(pk__in=[])
    for email in {(post.email or '').strip(), (post.booker_email or '').strip()} - {''}:
        q |= Q(email__iexact=email)
    if (post.name or '').strip():
        q |= Q(name__iexact=post.name.strip())

    rows = [pm for pm in PaypalPayment.objects.filter(q, amount__lt=0)
            if pm.kind == PaypalPayment.KIND_REFUND]
    rows += list(StripePayment.objects.filter(q, amount__lt=0))
    return rows


def _classify_cancelled_post(post, paid):
    """(status, note) for a cancelled booking that still carries a paid amount.

    Cancelled bookings are already excluded from 1A, so the only question is
    whether the customer got the money back. Money kept (cancellation fee,
    no-show) is revenue that is currently missing from 1A.
    """
    refunds = _payer_refunds(post)
    full = {paid, (paid * _PAYPAL_SURCHARGE_RATE).quantize(_CENT, rounding=ROUND_HALF_UP)}
    for pm in refunds:
        amt = abs(pm.amount)
        # >= paid also covers one refund for both legs of a return booking.
        if any(_near(amt, f) for f in full) or amt >= paid:
            return 'ok', (f"Refunded ${amt} on {pm.created:%Y-%m-%d} — "
                          f"booking already excluded from 1A, nothing to do.")
    if refunds:
        amounts = ', '.join(f"${abs(pm.amount)} ({pm.created:%Y-%m-%d})" for pm in refunds)
        return 'warn', (f"Refund on record ({amounts}) doesn't match paid ${paid}. "
                        f"Any part kept (e.g. cancellation fee) is revenue missing from 1A.")
    return 'warn', ("No PayPal/Stripe refund on record. Refunded by bank → OK. "
                    "Kept (fee / no-show / credit) → revenue missing from 1A.")


def _classify_refund_payment(pm, amt):
    """(status, note) for a negative PayPal/Stripe row in the quarter."""
    from datetime import timedelta
    from blog.models import PaypalPayment
    from blog.blog_utils import match_posts_for_payer

    created = pm.created.date()
    posts = list(
        match_posts_for_payer(pm)
        .filter(pickup_date__gte=created - timedelta(days=180),
                pickup_date__lte=created + timedelta(days=365))
        .order_by('pickup_date')
    )
    active = [p for p in posts if not p.cancelled]

    if isinstance(pm, PaypalPayment) and pm.kind == PaypalPayment.KIND_DISPUTE:
        if not active:
            return 'ok', ("Dispute/chargeback — matching bookings are cancelled (excluded "
                          "from 1A) and the surcharge is netted automatically.")
        ids = ', '.join(f"#{p.pk} ({p.pickup_date})" for p in active)
        return 'check', (f"Dispute/chargeback ({pm.payment_status or 'reversal'}) — NOT a "
                         f"refund we issued. Active bookings still counted in 1A: {ids}. "
                         f"If PayPal kept the money, cancel or adjust those bookings.")

    if not posts:
        return 'check', ("No booking matched by email/name — find the booking and "
                         "enter Post.refund on it if it is still active.")

    base = _refund_base(pm, amt)
    # Cancelled bookings this refund (or another refund from the same payer)
    # fully covers — keyed on paid, or on Post.refund when paid was cleared.
    fully_refunded = set()
    for p in posts:
        if not p.cancelled:
            continue
        targets = {to_decimal_safe(p.paid), p.refund or ZERO} - {ZERO}
        if any(_near(amt, v) or _near(base, v) for v in targets):
            return 'ok', f"Cancelled booking #{p.pk} ({p.pickup_date}) — already excluded from 1A."
        for other in _payer_refunds(p):
            o_amt = abs(other.amount)
            if any(_near(o_amt, v) or _near(_refund_base(other, o_amt), v) for v in targets):
                fully_refunded.add(p.pk)
    for p in active:
        refund = p.refund or ZERO
        if refund > ZERO and _near(refund, base):
            return 'ok', f"Netted via Post.refund ${refund} on #{p.pk} ({p.pickup_date})."
        if refund > ZERO and _near(refund, amt) and base != amt:
            return 'warn', (f"Post.refund on #{p.pk} is ${refund} incl. surcharge — "
                            f"should be ${base} (surcharge is netted separately).")
    for p in posts:
        if (p.cancelled and p.pk not in fully_refunded
                and amt < to_decimal_safe(p.paid) * _PAYPAL_SURCHARGE_RATE):
            return 'warn', (f"Partial refund on cancelled booking #{p.pk} ({p.pickup_date}) — "
                            f"the part kept is revenue missing from 1A.")
    ids = ', '.join(f"#{p.pk} ({p.pickup_date})" for p in active) or 'none'
    return 'check', (f"Not linked to a cancelled booking or Post.refund. If it belongs to "
                     f"an active booking ({ids}), enter Post.refund = ${base} on it.")


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
    # needs_review (held for triage) and excluded (driver payouts already in
    # settlements) rows are NOT claimed as 1B until approved in the admin.
    gst_1b = ZERO
    for tx in Transaction.objects.filter(
        date__gte=start, date__lte=end,
        direction='expense', gst_code='gst',
        needs_review=False, excluded=False, is_tax_deductible=True,
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
    # Each row carries a status so the list can be triaged at a glance:
    #   ok    — already handled (cancelled booking excluded / Post.refund set)
    #   warn  — possible revenue missing from 1A (money kept on a cancelled
    #           booking) or a Post.refund entered on the wrong basis
    #   check — needs a human (dispute, refund not linked to any booking)
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
        .only('paid', 'name', 'email', 'booker_email', 'pickup_date')
    ):
        paid = to_decimal_safe(post.paid)
        if paid > ZERO:
            status, note = _classify_cancelled_post(post, paid)
            refund_candidates.append({
                'source': 'Cancelled booking',
                'description': f"{post.name} / {post.email} — {post.pickup_date}",
                'amount': paid,
                'gst_ref': (paid / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP),
                'status': status,
                'note': note,
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
        ):
            amt = abs(pm.amount)
            status, note = _classify_refund_payment(pm, amt)
            is_dispute = (
                PayModel is PaypalPayment
                and pm.kind == PaypalPayment.KIND_DISPUTE
            )
            refund_candidates.append({
                'source': 'PayPal dispute' if is_dispute else label,
                'description': f"{pm.name} / {pm.email} — {pm.created:%Y-%m-%d}",
                'amount': amt,
                'gst_ref': (amt / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP),
                'status': status,
                'note': note,
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
    from blog.models import Post

    if brand not in VALID_BRANDS:
        brand = BRAND_ALL

    # Held-for-review and excluded rows are not finalised figures: keep them out
    # of P&L until triaged (excluded driver payouts are already in settlements).
    tx = Transaction.objects.filter(
        date__gte=start, date__lte=end,
        needs_review=False, excluded=False,
    )
    if brand != BRAND_ALL:
        tx = tx.filter(brand=brand)

    income_transactions = _sum(tx.filter(direction='income'), 'gross_amount')

    # Booking income — Post has no brand field (all Post rows are shuttle),
    # so this only applies to the 'all' and 'shuttle' views. Excludes
    # cancelled bookings and cash a non-owner driver collected directly
    # (driver_collected_cash — not company revenue); owner drivers' cash stays
    # in. Nets each row's refund off its paid amount (mirrors build_sales_gst).
    income_bookings = ZERO
    income_paypal_surcharge = ZERO
    if brand in (BRAND_ALL, 'shuttle'):
        posts = (
            Post.objects
            .filter(pickup_date__gte=start, pickup_date__lte=end,
                    cancelled=False, driver_collected_cash=False)
            .exclude(paid__isnull=True).exclude(paid='').exclude(paid='TBA')
            .only('paid', 'refund')
        )
        for post in posts:
            net = to_decimal_safe(post.paid) - (post.refund or ZERO)
            if net > ZERO:
                income_bookings += net
        income_paypal_surcharge = paypal_surcharge_total(start, end)

    income_total = income_transactions + income_bookings + income_paypal_surcharge

    expense_qs = tx.filter(direction='expense')

    # Non-deductible rows (e.g. fines/infringements, is_tax_deductible=False)
    # are imported for record-keeping but must never count as a business
    # expense — kept out of expense_total/expense_breakdown and reported
    # separately for visibility.
    deductible_expense_qs = expense_qs.filter(is_tax_deductible=True)
    expense_total = _sum(deductible_expense_qs, 'gross_amount')
    non_deductible_total = _sum(
        expense_qs.filter(is_tax_deductible=False), 'gross_amount')

    # category breakdown — grouped in the DB, not in python.
    expense_breakdown = list(
        deductible_expense_qs.values('category')
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
        'income_bookings': income_bookings,
        'income_paypal_surcharge': income_paypal_surcharge,
        'income_transactions': income_transactions,
        'expense_total': expense_total,
        'expense_breakdown': expense_breakdown,
        'non_deductible_total': non_deductible_total,
        'labour_total': labour_total,
        'labour_in_net': labour_in_net,
        'net': net,
        # for the "all" view, expense + labour is the total cost block
        'total_cost': (expense_total + labour_total) if is_all else expense_total,
    }
