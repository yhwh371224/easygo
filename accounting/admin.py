from datetime import date, timedelta

from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.dateparse import parse_date

from .models import Transaction, PaymentFeeLog, PayrollEntry, DividendRecord, DirectorLoan
from . import conf, reports


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'brand', 'direction', 'description', 'gross_amount',
                    'gst_code', 'category', 'is_tax_deductible', 'needs_review', 'excluded')
    list_filter = ('needs_review', 'excluded', 'is_tax_deductible', 'brand', 'direction',
                   'gst_code', 'source')
    date_hierarchy = 'date'
    search_fields = ('description', 'counterparty')
    change_list_template = 'admin/accounting/transaction/change_list.html'
    actions = ('approve_as_expense', 'exclude_as_driver_payment',
               'exclude_as_customer_refund', 'exclude_as_personal')

    @admin.action(description="경비 승인 — count as BAS 1B expense")
    def approve_as_expense(self, request, queryset):
        """Clear the review hold so the row counts as a normal 1B expense."""
        updated = queryset.update(needs_review=False, excluded=False)
        self.message_user(request, f"{updated} transaction(s) approved as expense.")

    @admin.action(description="드라이버 지급(제외) — exclude from BAS/P&L")
    def exclude_as_driver_payment(self, request, queryset):
        """Mark as a driver payout already captured by DriverSettlement, so it
        is permanently excluded from BAS/P&L (avoids double counting)."""
        updated = queryset.update(needs_review=False, excluded=True)
        self.message_user(request, f"{updated} transaction(s) excluded as driver payment.")

    @admin.action(description="고객 환불(제외) — exclude from BAS/P&L")
    def exclude_as_customer_refund(self, request, queryset):
        """Mark as a customer refund already captured on the booking (Post.refund,
        netted off 1A), so it is permanently excluded from BAS/P&L (avoids double
        counting). Only use after confirming the matching Post.refund was entered —
        if it wasn't, enter it there first, then exclude this bank row."""
        updated = queryset.update(needs_review=False, excluded=True)
        self.message_user(request, f"{updated} transaction(s) excluded as customer refund.")

    @admin.action(description="개인 지출(제외) — exclude + record as director loan")
    def exclude_as_personal(self, request, queryset):
        """Mark as a personal (non-business) purchase paid off the company account.

        Excluded from BAS/P&L and flagged non-deductible, then mirrored into
        DirectorLoan as a 'repayment' so the amount owed back shows on the loan
        balance. Use this for personal spend from a merchant that isn't in
        conf.PERSONAL_EXPENSE_MARKERS (those are handled on import).

        Saved row-by-row rather than via queryset.update() because each row needs
        its DirectorLoan entry created; the mirror is idempotent, so re-running
        the action on the same rows will not double-count.
        """
        updated = loans = 0
        for tx in queryset:
            tx.needs_review = False
            tx.excluded = True
            tx.is_tax_deductible = False
            tx.category = conf.PERSONAL_EXPENSE_CATEGORY
            tx.save(update_fields=['needs_review', 'excluded',
                                   'is_tax_deductible', 'category'])
            updated += 1
            if DirectorLoan.record_personal_expense(tx) is not None:
                loans += 1
        self.message_user(
            request,
            f"{updated}건을 개인 지출로 제외했습니다 — director loan {loans}건 기록, "
            f"잔액 ${DirectorLoan.current_balance()}.")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'pnl-report/',
                self.admin_site.admin_view(self.pnl_report_view),
                name='accounting_pnl_report',
            ),
            path(
                'bas-report/',
                self.admin_site.admin_view(self.bas_report_view),
                name='accounting_bas_report',
            ),
        ]
        return custom + urls

    def pnl_report_view(self, request):
        cur_fy = reports.current_fy_end_year()

        # Period: explicit start/end take priority; otherwise the financial year.
        start = parse_date(request.GET.get('start') or '')
        end = parse_date(request.GET.get('end') or '')

        try:
            fy_end_year = int(request.GET.get('fy') or cur_fy)
        except (TypeError, ValueError):
            fy_end_year = cur_fy

        if start and end:
            period_mode = 'custom'
        else:
            period_mode = 'fy'
            start, end = reports.fy_range(fy_end_year)

        brand = request.GET.get('brand') or reports.BRAND_ALL
        if brand not in reports.VALID_BRANDS:
            brand = reports.BRAND_ALL

        pnl = reports.build_pnl(start, end, brand)

        fy_choices = [
            {'value': y, 'label': f'FY{y} ({y - 1}-07 ~ {y}-06)'}
            for y in range(cur_fy - 4, cur_fy + 1)
        ]
        brand_choices = [
            {'value': reports.BRAND_ALL, 'label': 'All brands (combined)'},
            {'value': 'shuttle', 'label': 'Shuttle'},
            {'value': 'coaches', 'label': 'Coaches'},
        ]

        context = {
            **self.admin_site.each_context(request),
            'title': 'P&L Report',
            'opts': self.model._meta,
            'pnl': pnl,
            'period_mode': period_mode,
            'fy_end_year': fy_end_year,
            'fy_choices': fy_choices,
            'brand_choices': brand_choices,
            'start_str': start.isoformat() if start else '',
            'end_str': end.isoformat() if end else '',
        }
        return TemplateResponse(request, 'admin/accounting/pnl_report.html', context)

    def bas_report_view(self, request):
        cur_fy = reports.current_fy_end_year()

        try:
            fy_year = int(request.GET.get('fy_year') or cur_fy)
        except (TypeError, ValueError):
            fy_year = cur_fy

        try:
            fy_quarter = int(request.GET.get('fy_quarter') or 1)
            if fy_quarter not in (1, 2, 3, 4):
                fy_quarter = 1
        except (TypeError, ValueError):
            fy_quarter = 1

        bas = reports.build_bas(fy_year, fy_quarter)

        fy_choices = [
            {'value': y, 'label': f'FY{y}'}
            for y in range(cur_fy - 3, cur_fy + 2)
        ]
        quarter_choices = [
            {'value': q, 'label': label}
            for q, label in reports.QUARTER_LABELS.items()
        ]

        context = {
            **self.admin_site.each_context(request),
            'title': 'BAS Report',
            'opts': self.model._meta,
            'bas': bas,
            'fy_year': fy_year,
            'fy_quarter': fy_quarter,
            'fy_choices': fy_choices,
            'quarter_choices': quarter_choices,
        }
        return TemplateResponse(request, 'admin/accounting/bas_report.html', context)


@admin.register(PaymentFeeLog)
class PaymentFeeLogAdmin(admin.ModelAdmin):
    """Raw PayPal/Stripe fee rows awaiting monthly compaction into Transaction
    (see the compact_payment_fees command) — read here to check this month's
    fees before the 7th-of-next-month compaction runs."""
    list_display = ('date', 'source', 'brand', 'direction', 'description',
                    'gross_amount', 'gst_code', 'gst_amount')
    list_filter = ('source', 'brand', 'direction', 'gst_code')
    date_hierarchy = 'date'
    search_fields = ('description', 'counterparty')


@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ('pay_date', 'employee_name', 'gross_pay', 'paygw_withheld', 'super_amount', 'net_pay')
    date_hierarchy = 'pay_date'
    actions = ('duplicate_next_week',)

    @admin.action(description="다음 주로 복제 — copy with dates shifted +7 days")
    def duplicate_next_week(self, request, queryset):
        """Copy each selected entry, shifting pay_date/period_start/period_end
        by 7 days so the same weekly payroll doesn't need re-entering by hand."""
        created = 0
        for entry in queryset:
            entry.pk = None
            entry.pay_date += timedelta(days=7)
            entry.period_start += timedelta(days=7)
            entry.period_end += timedelta(days=7)
            entry.save()
            created += 1
        self.message_user(request, f"{created}건을 다음 주 날짜로 복제했습니다.")


@admin.register(DividendRecord)
class DividendRecordAdmin(admin.ModelAdmin):
    list_display = ('declared_date', 'amount', 'franking_credit', 'status')
    list_filter = ('status',)
    date_hierarchy = 'declared_date'


@admin.register(DirectorLoan)
class DirectorLoanAdmin(admin.ModelAdmin):
    list_display  = ('date', 'direction', 'amount', 'description')
    list_filter   = ('direction',)
    date_hierarchy = 'date'
    change_list_template = 'admin/accounting/directorloan/change_list.html'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['director_loan_balance'] = DirectorLoan.current_balance()
        return super().changelist_view(request, extra_context=extra_context)
