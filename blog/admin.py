from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from .models import Driver, DriverSettlement, Inquiry, PaypalPayment, PhoneMapping, StripePayment, Post, VirtualNumber


class DriverAdmin(admin.ModelAdmin):
    list_display = ['order', 'driver_name', 'abn', 'driver_contact', 'driver_email', 'driver_plate', 'user', 'must_change_password', 'impersonate_button']
    search_fields = ['driver_name', 'abn', 'driver_contact', 'driver_email', 'driver_address', 'driver_plate']
    ordering = ['order']

    def impersonate_button(self, obj):
        if obj.user:
            url = reverse('blog:driver_impersonate', args=[obj.pk])
            return format_html('<a class="button" href="{}">Login as Driver</a>', url)
        return '-'
    impersonate_button.short_description = 'Impersonate'


@admin.register(DriverSettlement)
class DriverSettlementAdmin(admin.ModelAdmin):
    list_display = ['settlement_number', 'driver', 'from_date', 'to_date', 'total_amount', 'status', 'settled_by', 'settled_at']
    list_filter = ['status', 'driver']
    search_fields = ['settlement_number']
    readonly_fields = ['created_at']
    actions = ['action_lock_settlement', 'action_mark_paid']

    _MONEY_FIELDS = ['total_amount', 'cash_total', 'paid_total', 'gst_total']
    _NUMBER_FIELDS = ['settlement_number', 'rcti_number', 'from_date', 'to_date']

    def get_readonly_fields(self, request, obj=None):
        base = list(self.readonly_fields)
        if obj and obj.status != 'draft':
            base += self._MONEY_FIELDS + self._NUMBER_FIELDS
        return base

    @admin.action(description='Lock settlement')
    def action_lock_settlement(self, request, queryset):
        from blog.services.settlement_service import lock_settlement
        for settlement in queryset:
            try:
                lock_settlement(settlement, request.user)
                self.message_user(request, f"Locked: {settlement.settlement_number}")
            except ValidationError as e:
                self.message_user(request, str(e), messages.ERROR)

    @admin.action(description='Mark as paid')
    def action_mark_paid(self, request, queryset):
        from blog.services.settlement_service import mark_paid
        for settlement in queryset:
            try:
                mark_paid(settlement, request.user, settlement.payment_method, timezone.now())
                self.message_user(request, f"Marked as paid: {settlement.settlement_number}")
            except ValidationError as e:
                self.message_user(request, str(e), messages.ERROR)

    def save_model(self, request, obj, form, change):
        obj.settled_by = request.user
        super().save_model(request, obj, form, change)


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
                    'suburb', 'street', 'start_point', 'end_point', 'region', 'meeting_point',
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
                    'cancelled', 'pending', 'cash', 'direction', 'return_flight_number', 'created']
    list_filter  = ['region', 'cancelled', 'pending', 'cash']
    search_fields = ['pickup_date', 'pickup_time', 'suburb', 'email', 'street', 'booker_email', 'booker_name',
                     'name', 'contact', 'price', 'paid', 'email1', 'message', 'notice', 'region__name']
    readonly_fields = ['suburb_distance_km', 'suburb_base_price']

    fieldsets = [
        ('Customer Info', {
            'fields': ['name', 'company_name', 'contact', 'email', 'email1',
                    'booker_name', 'booker_email']
        }),
        ('Pickup Info', {
            'fields': ['pickup_date', 'pickup_time', 'direction', 'flight_number', 'flight_time',
                    'suburb', 'street', 'start_point', 'end_point',
                    'region', 'terminal_pickup_point', 'meeting_point',
                    'no_of_passenger', 'no_of_baggage',
                    'extra_stop', 'extra_stop_addresses', 'same_extra_stop']
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
admin_site.register(Inquiry, InquiryAdmin)
admin_site.register(PaypalPayment, PaypalPaymentAdmin)
admin_site.register(StripePayment, StripePaymentAdmin)
admin_site.register(Post, PostAdmin)
admin_site.register(PhoneMapping, PhoneMappingAdmin)
admin_site.register(VirtualNumber, VirtualNumberAdmin)

admin.site.register(Driver, DriverAdmin)
admin.site.register(Inquiry, InquiryAdmin)
admin.site.register(PaypalPayment, PaypalPaymentAdmin)
admin.site.register(StripePayment, StripePaymentAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(PhoneMapping, PhoneMappingAdmin) 
admin.site.register(VirtualNumber, VirtualNumberAdmin)
