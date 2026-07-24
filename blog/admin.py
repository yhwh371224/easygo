import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

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
    list_display = ['order', 'driver_name', 'is_company', 'abn', 'gst_registered', 'commission_rate', 'driver_contact', 'driver_email', 'driver_plate', 'user', 'impersonate_button']
    list_editable = ['gst_registered', 'commission_rate']
    list_filter = ['gst_registered', 'is_company']
    search_fields = ['driver_name', 'abn', 'driver_contact', 'driver_email', 'driver_address', 'driver_plate']
    ordering = ['order']
    readonly_fields = ['agreement_link_display']

    def impersonate_button(self, obj):
        if obj.user:
            url = reverse('blog:driver_impersonate', args=[obj.pk])
            return format_html('<a class="button" href="{}">Login as Driver</a>', url)
        return '-'
    impersonate_button.short_description = 'Impersonate'

    def agreement_link_display(self, obj):
        from django.conf import settings
        if not obj.pk or not obj.agreement_token:
            return '-'
        path = reverse('blog:driver_agreement_public', args=[obj.agreement_token])
        url = f"{settings.SITE_URL}{path}"
        return format_html(
            '<input type="text" readonly style="width:480px" value="{0}" '
            'onclick="this.select()"> <a class="button" href="{0}" target="_blank">Open</a>'
            '<div style="color:#666;font-size:.85em;margin-top:.3em;">'
            'No-login link — send this to the subcontractor so they can review '
            '&amp; confirm the agreement before they have a portal login.</div>',
            url,
        )
    agreement_link_display.short_description = 'Agreement link (no login)'


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
    list_display = ['driver', 'version', 'confirmed_at', 'signed_by_name',
                    'signed_by_title', 'gst_registered_snapshot', 'ip_address']
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
                     'booker_contact', 'name', 'contact', 'email1', 'message', 'notice', 'region__name']
    readonly_fields = ['suburb_distance_km', 'suburb_base_price']

    fieldsets = [
        ('Customer Info', {
            'fields': ['name', 'company_name', 'contact', 'email', 'email1',
                    'booker_name', 'booker_email', 'booker_contact']
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
                    'private_ride','cruise',  'no_email_reminder']
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
    list_display = ['pickup_date', 'region', 'name', 'suburb', 'pickup_time', 'price', 'paid', 'driver_price',
                    'cancelled', 'pending', 'cash', 'sent_email', 'direction', 'return_flight_number', 'created']
    list_filter  = ['region', 'cancelled', 'pending', 'cash']
    search_fields = ['pickup_date', 'pickup_time', 'suburb', 'email', 'street', 'booker_email', 'booker_name',
                     'booker_contact', 'name', 'contact', 'price', 'paid', 'email1', 'message', 'notice', 'region__name']
    readonly_fields = ['suburb_distance_km', 'suburb_base_price', 'commission_amount_display', 'subcontractor_payout_display']
    actions = ['duplicate_bookings']

    # price / paid / driver_price are CharFields holding numeric strings, so
    # halving means parsing the number out, dividing by 2, and reformatting.
    @staticmethod
    def _halve_amount(val):
        if val is None:
            return val
        s = str(val).strip()
        if not s:
            return val
        cleaned = re.sub(r'[^0-9.\-]', '', s)  # tolerate '$', commas, spaces
        try:
            halved = (Decimal(cleaned) / Decimal('2')).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError):
            return val  # non-numeric — leave untouched
        out = format(halved, 'f')
        if '.' in out:
            out = out.rstrip('0').rstrip('.')  # 75.00 -> 75, 77.50 -> 77.5
        return out

    # no_of_passenger / no_of_baggage are CharFields holding whole-number
    # counts — halve, then round to a whole number so no decimal ever shows
    # (e.g. '3' -> 2, '5' -> 3).
    @staticmethod
    def _halve_count(val):
        if val is None:
            return val
        s = str(val).strip()
        if not s:
            return val
        cleaned = re.sub(r'[^0-9.\-]', '', s)
        try:
            halved = (Decimal(cleaned) / Decimal('2')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            return val  # non-numeric — leave untouched
        return str(halved)

    # no_of_baggage is a comma-joined summary of label+count tokens, e.g.
    # 'L5, S4' or 'L2, M1, Ski2(Oversize)'. Halve the count in each token while
    # keeping the label and any '(Oversize)' marker (round half up, never 0).
    @staticmethod
    def _halve_baggage(val):
        if val is None:
            return val
        s = str(val).strip()
        if not s:
            return val
        out = []
        for tok in (t.strip() for t in s.split(',')):
            if not tok:
                continue
            m = re.match(r'^([A-Za-z]+)\s*(\d+)\s*(.*)$', tok)
            if not m:
                out.append(tok)  # unexpected shape — leave untouched
                continue
            label, qty, rest = m.group(1), m.group(2), m.group(3).strip()
            halved = (Decimal(qty) / Decimal('2')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            if halved <= 0:
                continue  # count rounded to 0 — drop the item
            out.append(f'{label}{halved}{rest}')
        return ', '.join(out)

    @admin.action(description='Duplicate selected booking(s)')
    def duplicate_bookings(self, request, queryset):
        created = 0
        for obj in queryset:
            # Split the money in half: the original keeps one half, the copy
            # gets the other. Halve the original in place first, then save it.
            half_price = self._halve_amount(obj.price)
            half_paid = self._halve_amount(obj.paid)
            half_driver_price = self._halve_amount(obj.driver_price)
            half_passenger = self._halve_count(obj.no_of_passenger)
            half_baggage = self._halve_baggage(obj.no_of_baggage)

            obj.price = half_price
            obj.paid = half_paid
            obj.driver_price = half_driver_price
            obj.no_of_passenger = half_passenger
            obj.no_of_baggage = half_baggage
            # Let the original sync so its existing calendar event updates to the
            # new half price (sync_to_calendar edits in place when an event id
            # already exists — no duplicate-event race here, only the copy needs
            # the skip below).
            obj.save()

            # Now turn the same instance into a brand-new copy carrying the
            # other half.
            obj.pk = None
            obj._state.adding = True
            obj.calendar_event_id = ''
            obj.driver_calendar_event_id = ''
            obj.driver = None
            obj.use_proxy = False
            obj.price = half_price
            obj.paid = half_paid
            obj.driver_price = half_driver_price
            obj.no_of_passenger = half_passenger
            obj.no_of_baggage = half_baggage
            # The copy is an internal split — don't send it an email reminder,
            # and don't send it a review request either.
            obj.no_email_reminder = True
            obj.no_review = True
            # Skip calendar sync on this initial copy — otherwise it races with the
            # user's follow-up edit-and-save and creates two events for one booking.
            # The follow-up save (without this flag) is what actually creates the event.
            obj._skip_calendar_sync = True
            obj.save()
            created += 1
        self.message_user(
            request,
            f'Duplicated {created} booking(s). Assign a driver on each copy.',
            messages.SUCCESS,
        )

    fieldsets = [
        ('Customer Info', {
            'fields': ['name', 'company_name', 'contact', 'email', 'email1',
                    'booker_name', 'booker_email', 'booker_contact']
        }),
        ('Pickup Info', {
            'fields': ['pickup_date', 'pickup_time', 'direction', 'flight_number', 'flight_time',
                    'suburb', 'street', 'start_point', 'end_point',
                    'region', 'terminal_pickup_point', 'customer_history',
                    'no_of_passenger', 'no_of_baggage',
                    'extra_stop', 'extra_stop_addresses', 'same_extra_stop', 'extra_stop_area']
        }),
        ('Return Info', {
            'fields': ['return_direction', 'return_pickup_date', 'return_pickup_time',
                    'return_flight_number', 'return_flight_time',
                    'return_start_point', 'return_end_point']
        }),
        ('Pricing', {
            'fields': ['suburb_distance_km', 'suburb_base_price', 'price', 'paid', 'discount', 'toll', 'surcharge',
                       'driver_price', 'commission_rate', 'commission_amount_override', 'commission_amount_display', 'subcontractor_payout_display',
                       'deposit_amount_due', 'refund', 'driver_refund_deduction']
        }),
        ('Status', {
            'fields': ['is_confirmed', 'cancelled', 'pending', 'sent_email', 'reminder', 'cash', 'driver_collected_cash', 'prepay',
                    'private_ride','cruise',  'no_email_reminder', 'no_review']
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
    list_display = ['pickup_date', 'pickup_time', 'driver_name', 'post', 'from_number', 'to_number', 'created_at']
    search_fields = ['from_number', 'to_number', 'driver_name', 'pickup_date']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    autocomplete_fields = ['post']


class VirtualNumberAdmin(admin.ModelAdmin):
    list_display = ['number', 'is_wired']
    search_fields = ['number']
    readonly_fields = ['sms_channel_id', 'voice_channel_id']

    # Channel ids come from Bird via `manage.py sync_bird_channels`; typing one
    # by hand would claim a number is routable when it isn't.
    @admin.display(boolean=True, description='Wired to Bird')
    def is_wired(self, obj):
        return obj.is_wired


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
