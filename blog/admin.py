from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.html import format_html
from django.urls import reverse
from .models import Driver, DriverSettlement, Inquiry, PaypalPayment, PhoneMapping, StripePayment, Post, VirtualNumber


class DriverAdmin(admin.ModelAdmin):
    list_display = ['driver_name', 'driver_contact', 'driver_email', 'driver_plate', 'user', 'must_change_password', 'impersonate_button']
    search_fields = ['driver_name', 'driver_contact', 'driver_email', 'driver_address', 'driver_plate']

    def impersonate_button(self, obj):
        if obj.user:
            url = reverse('blog:driver_impersonate', args=[obj.pk])
            return format_html('<a class="button" href="{}">Login as Driver</a>', url)
        return '-'
    impersonate_button.short_description = 'Impersonate'


@admin.register(DriverSettlement)
class DriverSettlementAdmin(admin.ModelAdmin):
    list_display = ['driver', 'amount', 'note', 'settled_by', 'settled_at']
    list_filter = ['driver']
    
    def save_model(self, request, obj, form, change):
        obj.settled_by = request.user
        super().save_model(request, obj, form, change)


class InquiryAdmin(admin.ModelAdmin):
    list_display = ['pickup_date', 'suburb', 'pickup_time', 'direction', 'no_of_passenger', 'return_flight_number','is_confirmed',
                    'cancelled', 'pending', 'created']
    search_fields = ['pickup_date', 'pickup_time', 'suburb', 'email', 'street', 'booker_email', 'booker_name',
                     'name', 'contact', 'email1', 'message', 'notice', 'region__name']


class PaypalPaymentAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'amount', 'txn_id', 'created']    
    search_fields = ['name', 'email', 'amount']


class StripePaymentAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'amount', 'payment_intent_id', 'created']    
    search_fields = ['name', 'email', 'amount']


class PostAdmin(admin.ModelAdmin):
    list_display = ['pickup_date', 'name', 'suburb', 'pickup_time', 'price', 'paid',
                    'cancelled', 'pending', 'cash', 'direction', 'return_flight_number', 'created']
    search_fields = ['pickup_date', 'pickup_time', 'suburb', 'email', 'street', 'booker_email', 'booker_name',
                     'name', 'contact', 'price', 'paid', 'email1', 'message', 'notice', 'region__name']


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
