from django.contrib import admin
from .models import Post, Inquiry, Payment, Driver
from rangefilter.filters import DateRangeFilter
from django.contrib.admin import AdminSite


class PostAdmin(admin.ModelAdmin):
    list_display = ['flight_date', 'contact', 'name', 'suburb', 'street',
                    'pickup_time', 'price', 'paid', 
                    'cancelled', 'direction', 'return_flight_number',
                     ]

    list_filter = (('flight_date', DateRangeFilter), 'suburb')

    search_fields = ['flight_date', 'pickup_time', 'suburb', 'email', 'street', 
                     'name', 'contact']


class InquiryAdmin(admin.ModelAdmin):
    list_display = ['flight_date', 'contact', 'name', 'suburb', 'street', 
                    'pickup_time', 'price', 'is_confirmed', 
                    'cancelled', 'direction', 'return_flight_number',
                     ]

    list_filter = (('flight_date', DateRangeFilter), 'suburb')

    search_fields = ['flight_date', 'pickup_time', 'suburb', 'email', 'street', 
                     'name', 'contact']
    

class PaymentAdmin(admin.ModelAdmin):
    list_display = ['item_name', 'payer_email', 'gross_amount', 'txn_id', 'created']    
    

    search_fields = ['item_name', 'payer_email', 'gross_amount']


class DriverAdmin(admin.ModelAdmin):
    list_display = ['driver_name', 'driver_contact', 'driver_email', 'driver_address', 'driver_plate']

    search_fields = ['driver_name', 'driver_contact', 'driver_email', 'driver_address', 'driver_plate']



class MyAdminSite(AdminSite):
    site_header = 'EasyGo administration'

admin_site = MyAdminSite(name='horeb_yhwh')
admin_site.register(Post, PostAdmin)
admin_site.register(Inquiry, InquiryAdmin)
admin_site.register(Payment, PaymentAdmin)
admin_site.register(Driver, DriverAdmin)   
    

admin.site.register(Post, PostAdmin)
admin.site.register(Inquiry, InquiryAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Driver, DriverAdmin)