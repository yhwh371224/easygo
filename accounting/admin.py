from datetime import date

from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.dateparse import parse_date

from .models import Transaction, PayrollEntry, DividendRecord
from . import reports


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'brand', 'direction', 'description', 'gross_amount', 'gst_code', 'category')
    list_filter = ('brand', 'direction', 'gst_code', 'source')
    date_hierarchy = 'date'
    search_fields = ('description', 'counterparty')

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'pnl-report/',
                # admin_view enforces staff login; keeps the report admin-only.
                self.admin_site.admin_view(self.pnl_report_view),
                name='accounting_pnl_report',
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


@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ('pay_date', 'employee_name', 'gross_pay', 'paygw_withheld', 'super_amount', 'net_pay')
    date_hierarchy = 'pay_date'


@admin.register(DividendRecord)
class DividendRecordAdmin(admin.ModelAdmin):
    list_display = ('declared_date', 'amount', 'franking_credit', 'status')
    list_filter = ('status',)
    date_hierarchy = 'declared_date'
