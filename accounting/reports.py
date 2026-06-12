"""P&L aggregation for the accounting admin report.

Scope (this step): accounting's own data only — Transaction + PayrollEntry.
Do NOT import blog's Post / DriverSettlement / payment models here.

This module is admin-only. Public views/templates must never import it.
All totals use ORM aggregate(Sum); no python-loop summation of rows.
"""
from datetime import date
from decimal import Decimal

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
