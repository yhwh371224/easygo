from django.contrib import admin
from django.contrib.admin import AdminSite
from .models import Driver, Inquiry, PaypalPayment, StripePayment, Post


class DriverAdmin(admin.ModelAdmin):
    list_display = ['driver_name', 'driver_contact', 'driver_email', 'driver_address', 'driver_plate']
    search_fields = ['driver_name', 'driver_contact', 'driver_email', 'driver_address', 'driver_plate']


class InquiryAdmin(admin.ModelAdmin):
    list_display = ['pickup_date', 'contact', 'name', 'suburb', 'pickup_time', 'price', 'is_confirmed', 
                    'cancelled', 'pending', 'direction', 'return_flight_number', 'created']
    search_fields = ['pickup_date', 'pickup_time', 'suburb', 'email', 'street', 
                     'name', 'contact', 'email1']


class PaypalPaymentAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'amount', 'txn_id', 'created']    
    search_fields = ['name', 'email', 'amount']


class StripePaymentAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'amount', 'payment_intent_id', 'created']    
    search_fields = ['name', 'email', 'amount']


class PostAdmin(admin.ModelAdmin):
    list_display = ['pickup_date', 'contact', 'name', 'suburb', 'pickup_time', 'price', 
                    'paid', 'cancelled', 'direction', 'return_flight_number', 'created']
    search_fields = ['pickup_date', 'pickup_time', 'suburb', 'email', 'street', 
                     'name', 'contact', 'price', 'paid', 'email1']
    # list_filter = ['paid']


class MyAdminSite(AdminSite):
    site_header = 'EasyGo administration'

admin_site = MyAdminSite(name='horeb_yhwh')
admin_site.register(Driver, DriverAdmin)
admin_site.register(Inquiry, InquiryAdmin)
admin_site.register(PaypalPayment, PaypalPaymentAdmin)
admin_site.register(StripePayment, StripePaymentAdmin)
admin_site.register(Post, PostAdmin)

admin.site.register(Driver, DriverAdmin)
admin.site.register(Inquiry, InquiryAdmin)
admin.site.register(PaypalPayment, PaypalPaymentAdmin)
admin.site.register(StripePayment, StripePaymentAdmin)
admin.site.register(Post, PostAdmin)
