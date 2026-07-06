from datetime import date

from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django import forms
from django.template.response import TemplateResponse
from django.urls import path as url_path, reverse
from django.utils.html import format_html
from .models import Driver, DriverSettlement, Inquiry, PaypalPayment, PhoneMapping, StripePayment, Post, VirtualNumber
from .models.driver import DriverSettlementItem, DriverAgreement


class CreateSettlementForm(forms.Form):
    driver = forms.ModelChoiceField(
        queryset=Driver.objects.order_by('order'),
        empty_label='— select driver —',
    )
    from_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='From date',
    )
    to_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='To date',
        initial=date.today,
    )


class DriverAdmin(admin.ModelAdmin):
    list_display = ['order', 'driver_name', 'abn', 'gst_registered', 'commission_rate', 'driver_contact', 'driver_email', 'driver_plate', 'user', 'must_change_password', 'impersonate_button']
    list_editable = ['gst_registered', 'commission_rate']
    list_filter = ['gst_registered']
    search_fields = ['driver_name', 'abn', 'driver_contact', 'driver_email', 'driver_address', 'driver_plate']
    ordering = ['order']

    def impersonate_button(self, obj):
        if obj.user:
            url = reverse('blog:driver_impersonate', args=[obj.pk])
            return format_html('<a class="button" href="{}">Login as Driver</a>', url)
        return '-'
    impersonate_button.short_description = 'Impersonate'


class DriverSettlementItemInline(admin.TabularInline):
    model = DriverSettlementItem
    extra = 0
    raw_id_fields = ['post']
    fields = ['post', 'amount', 'gst_amount', 'line_total', 'description']


@admin.register(DriverSettlement)
class DriverSettlementAdmin(admin.ModelAdmin):
    list_display = ['settlement_number', 'driver', 'from_date', 'to_date', 'total_amount', 'settled_by', 'settled_at']
    list_filter = ['driver']
    search_fields = ['settlement_number']
    inlines = [DriverSettlementItemInline]
    # Totals are derived from the line items (recomputed on save), and the
    # settlement number / status are system-managed — shown read-only.
    readonly_fields = ['created_at', 'settlement_number', 'status',
                       'total_amount', 'cash_total', 'paid_total', 'gst_total']
    # Xero is not used (bookkeeping is done in e-PayDay Go) — hide those fields.
    exclude = ['xero_exported', 'xero_exported_at', 'xero_reference',
               'xero_invoice_id']
    change_list_template = 'admin/blog/driversettlement/change_list.html'

    # ── Custom URL + view ───────────────────────────────────────────

    def get_urls(self):
        custom = [
            url_path(
                'create-settlement/',
                self.admin_site.admin_view(self.create_settlement_view),
                name='blog_driversettlement_create',
            ),
        ]
        return custom + super().get_urls()

    def create_settlement_view(self, request):
        from blog.services.settlement_service import SettlementService

        if request.method == 'POST':
            form = CreateSettlementForm(request.POST)
            if form.is_valid():
                driver     = form.cleaned_data['driver']
                from_date  = form.cleaned_data['from_date']
                to_date    = form.cleaned_data['to_date']

                settlement = SettlementService.create_settlement(
                    driver, from_date, to_date, user=request.user
                )

                if settlement is None:
                    self.message_user(
                        request,
                        f"No trips found for {driver.driver_name} "
                        f"between {from_date} and {to_date}.",
                        messages.WARNING,
                    )
                else:
                    self.message_user(
                        request,
                        f"Settlement {settlement.settlement_number} created "
                        f"(paid total: ${settlement.paid_total}). "
                        "It is recorded and editable below — adjust the line "
                        "items if anything is wrong.",
                    )
                    return self._redirect_to_change(settlement)
        else:
            form = CreateSettlementForm(initial={'to_date': date.today()})

        context = {
            **self.admin_site.each_context(request),
            'title': 'Create Settlement',
            'form': form,
            'opts': self.model._meta,
            'media': self.media + form.media,
        }
        return TemplateResponse(
            request,
            'admin/blog/driversettlement/create_settlement.html',
            context,
        )

    def _redirect_to_change(self, settlement):
        from django.http import HttpResponseRedirect
        url = reverse(
            f'{self.admin_site.name}:blog_driversettlement_change',
            args=[settlement.pk],
        )
        return HttpResponseRedirect(url)

    # ── Inject "Create Settlement" URL into changelist context ──────

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            extra_context['create_settlement_url'] = reverse(
                f'{self.admin_site.name}:blog_driversettlement_create'
            )
        except Exception:
            pass
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        # Settlements are only ever created through the custom "Create
        # Settlement" flow (which pulls the driver's trips and computes the
        # numbers). Disable the default admin "Add" so the raw blank form —
        # which can't produce a valid settlement number/totals — is never used.
        return False

    def save_model(self, request, obj, form, change):
        obj.settled_by = request.user
        if not obj.status:
            obj.status = 'paid'
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        """After the line items are saved, re-derive the totals and re-sync the
        BAS 1B expense so the books always match the edited settlement."""
        super().save_related(request, form, formsets, change)
        from blog.services.settlement_service import (
            recompute_totals, sync_settlement_expense,
        )
        settlement = form.instance
        recompute_totals(settlement)
        sync_settlement_expense(settlement)

    def delete_model(self, request, obj):
        from blog.services.settlement_service import delete_settlement_expense
        delete_settlement_expense(obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        from blog.services.settlement_service import delete_settlement_expense
        for obj in queryset:
            delete_settlement_expense(obj)
        super().delete_queryset(request, queryset)


class ConfirmedFilter(admin.SimpleListFilter):
    """Filter agreements by whether they've actually been confirmed yet."""
    title = 'confirmed'
    parameter_name = 'confirmed'

    def lookups(self, request, model_admin):
        return [('yes', 'Confirmed'), ('no', 'Not confirmed')]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(confirmed_at__isnull=False)
        if self.value() == 'no':
            return queryset.filter(confirmed_at__isnull=True)
        return queryset


class DriverAgreementAdmin(admin.ModelAdmin):
    list_display = ['driver', 'version', 'confirmed_at', 'gst_registered_snapshot',
                    'ip_address']
    list_filter = [ConfirmedFilter, 'version', 'gst_registered_snapshot', 'driver']
    search_fields = ['driver__driver_name', 'driver__abn', 'version']
    readonly_fields = ['created_at', 'confirmed_at', 'ip_address',
                       'gst_registered_snapshot']
    ordering = ['-created_at']


class InquiryAdmin(admin.ModelAdmin):
    list_display = ['pickup_date', 'region', 'suburb', 'pickup_time', 'direction', 'no_of_passenger',
                    'return_flight_number', 'is_confirmed', 'cancelled', 'pending', 'created']
    list_filter  = ['region', 'is_confirmed', 'cancelled', 'pending']
    search_fields = ['pickup_date', 'pickup_time', 'suburb', 'email', 'street', 'booker_email', 'booker_name',
                     'name', 'contact', 'email1', 'message', 'notice', 'region__name']
    readonly_fields = ['suburb_distance_km', 'suburb_base_price']

    fieldsets = [
        ('Customer Info', {
            'fields': ['name', 'company_name', 'contact', 'email', 'email1',
                    'booker_name', 'booker_email']
        }),
        ('Pickup Info', {
            'fields': ['pickup_date', 'pickup_time', 'direction', 'flight_number', 'flight_time',
                    'suburb', 'street', 'start_point', 'end_point', 'region', 'customer_history',
                    'no_of_passenger', 'no_of_baggage', 'extra_stop', 'extra_stop_addresses', 'same_extra_stop']
        }),
        ('Return Info', {
            'fields': ['return_direction', 'return_pickup_date', 'return_pickup_time',
                    'return_flight_number', 'return_flight_time',
                    'return_start_point', 'return_end_point']
        }),
        ('Pricing', {
            'fields': ['suburb_distance_km', 'suburb_base_price', 'price', 'paid', 'discount', 'toll', 'surcharge']
        }),
        ('Status', {
            'fields': ['is_confirmed', 'cancelled', 'pending', 'sent_email', 'reminder', 'cash', 'prepay',
                    'private_ride','cruise',  'sms_reminder']
        }),
        ('Driver', {
            'fields': ['driver']
        }),
        ('Notes', {
            'fields': ['message', 'notice', 'special_items']
        }),
    ]

    def suburb_distance_km(self, obj):
        from regions.models import RegionSuburb
        rs = RegionSuburb.objects.filter(region=obj.region, name__iexact=obj.suburb).first()
        return f"{rs.distance_km} km" if rs and rs.distance_km is not None else "-"
    suburb_distance_km.short_description = "Distance (km)"

    def suburb_base_price(self, obj):
        from regions.models import RegionSuburb
        rs = RegionSuburb.objects.filter(region=obj.region, name__iexact=obj.suburb).first()
        return f"${rs.price}" if rs else "-"
    suburb_base_price.short_description = "Base Price"


class PaypalPaymentAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'amount', 'txn_id', 'created']    
    search_fields = ['name', 'email', 'amount']


class StripePaymentAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'amount', 'payment_intent_id', 'created']    
    search_fields = ['name', 'email', 'amount']


class PostAdmin(admin.ModelAdmin):
    list_display = ['pickup_date', 'region', 'name', 'suburb', 'pickup_time', 'price', 'paid',
                    'cancelled', 'pending', 'cash', 'sent_email', 'direction', 'return_flight_number', 'created']
    list_filter  = ['region', 'cancelled', 'pending', 'cash']
    search_fields = ['pickup_date', 'pickup_time', 'suburb', 'email', 'street', 'booker_email', 'booker_name',
                     'name', 'contact', 'price', 'paid', 'email1', 'message', 'notice', 'region__name']
    readonly_fields = ['suburb_distance_km', 'suburb_base_price', 'commission_amount_display', 'subcontractor_payout_display']

    fieldsets = [
        ('Customer Info', {
            'fields': ['name', 'company_name', 'contact', 'email', 'email1',
                    'booker_name', 'booker_email']
        }),
        ('Pickup Info', {
            'fields': ['pickup_date', 'pickup_time', 'direction', 'flight_number', 'flight_time',
                    'suburb', 'street', 'start_point', 'end_point',
                    'region', 'terminal_pickup_point', 'customer_history',
                    'no_of_passenger', 'no_of_baggage',
                    'extra_stop', 'extra_stop_addresses', 'same_extra_stop']
        }),
        ('Return Info', {
            'fields': ['return_direction', 'return_pickup_date', 'return_pickup_time',
                    'return_flight_number', 'return_flight_time',
                    'return_start_point', 'return_end_point']
        }),
        ('Pricing', {
            'fields': ['suburb_distance_km', 'suburb_base_price', 'price', 'paid', 'discount', 'toll', 'surcharge',
                       'commission_rate', 'commission_amount_override', 'commission_amount_display', 'subcontractor_payout_display',
                       'deposit_amount_due']
        }),
        ('Status', {
            'fields': ['is_confirmed', 'cancelled', 'pending', 'sent_email', 'reminder', 'cash', 'driver_collected_cash', 'prepay',
                    'private_ride','cruise',  'sms_reminder']
        }),
        ('Driver', {
            'fields': ['driver', 'use_proxy']
        }),
        ('Notes', {
            'fields': ['message', 'notice', 'special_items']
        }),
        ('Calendar', {
            'fields': ['calendar_event_id', 'driver_calendar_event_id']
        }),
    ]

    def save_model(self, request, obj, form, change):
        if change:
            for field in ('calendar_event_id', 'driver_calendar_event_id'):
                submitted = (form.cleaned_data.get(field) or '').strip()
                if submitted:
                    continue
                initial = (form.initial.get(field) or '').strip()
                if initial:
                    continue
                db_val = (
                    Post.objects.filter(pk=obj.pk)
                    .values_list(field, flat=True)
                    .first() or ''
                ).strip()
                if db_val:
                    setattr(obj, field, db_val)
        # 드라이버 배정 시 commission_rate가 0이면 드라이버 기본 요율 자동 적용
        if obj.driver and not obj.commission_rate:
            obj.commission_rate = obj.driver.commission_rate
        super().save_model(request, obj, form, change)

    def suburb_distance_km(self, obj):
        from regions.models import RegionSuburb
        rs = RegionSuburb.objects.filter(region=obj.region, name__iexact=obj.suburb).first()
        return f"{rs.distance_km} km" if rs and rs.distance_km is not None else "-"
    suburb_distance_km.short_description = "Distance (km)"

    def suburb_base_price(self, obj):
        from regions.models import RegionSuburb
        rs = RegionSuburb.objects.filter(region=obj.region, name__iexact=obj.suburb).first()
        return f"${rs.price}" if rs else "-"
    suburb_base_price.short_description = "Base Price"

    def commission_amount_display(self, obj):
        if obj.commission_amount_override is not None:
            return f"${obj.commission_amount} (flat override)"
        return f"${obj.commission_amount} ({obj.commission_rate}%)"
    commission_amount_display.short_description = "Commission"

    def subcontractor_payout_display(self, obj):
        return f"${obj.subcontractor_payout}"
    subcontractor_payout_display.short_description = "Subcontractor Payout"


class PhoneMappingAdmin(admin.ModelAdmin):
    list_display = ['pickup_date', 'pickup_time', 'driver_name', 'from_number', 'to_number', 'created_at']
    search_fields = ['from_number', 'to_number', 'driver_name', 'pickup_date']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


class VirtualNumberAdmin(admin.ModelAdmin):
    list_display = ['number']
    search_fields = ['number']


class MyAdminSite(AdminSite):
    site_header = 'EasyGo administration'

admin_site = MyAdminSite(name='horeb_yhwh')
admin_site.register(Driver, DriverAdmin)
admin_site.register(DriverSettlement, DriverSettlementAdmin)
admin_site.register(DriverAgreement, DriverAgreementAdmin)
admin_site.register(Inquiry, InquiryAdmin)
admin_site.register(PaypalPayment, PaypalPaymentAdmin)
admin_site.register(StripePayment, StripePaymentAdmin)
admin_site.register(Post, PostAdmin)
admin_site.register(PhoneMapping, PhoneMappingAdmin)
admin_site.register(VirtualNumber, VirtualNumberAdmin)

admin.site.register(Driver, DriverAdmin)
admin.site.register(DriverAgreement, DriverAgreementAdmin)
admin.site.register(Inquiry, InquiryAdmin)
admin.site.register(PaypalPayment, PaypalPaymentAdmin)
admin.site.register(StripePayment, StripePaymentAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(PhoneMapping, PhoneMappingAdmin) 
admin.site.register(VirtualNumber, VirtualNumberAdmin)
