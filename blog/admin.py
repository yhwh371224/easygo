from django.contrib import admin
from .models import Post, Inquiry, Payment
from rangefilter.filters import DateRangeFilter


class PostAdmin(admin.ModelAdmin):
    list_display = ['flight_date', 'name', 'suburb', 'contact',
                    'created', 'price', 'is_confirmed', 'cancelled', 
                    'reConfirmed', 'return_flight_number',
                     ]

    list_filter = (('flight_date', DateRangeFilter), 'suburb')

    search_fields = ['flight_date', 'pickup_time', 'suburb', 'email', 
                     'name', 'contact']


class InquiryAdmin(admin.ModelAdmin):
    list_display = ['flight_date', 'name', 'suburb', 'contact',
                    'created', 'price', 'is_confirmed', 'cancelled', 
                    'reConfirmed', 'return_flight_number',
                     ]

    list_filter = (('flight_date', DateRangeFilter), 'suburb')

    search_fields = ['flight_date', 'pickup_time', 'suburb', 'email', 
                     'name', 'contact']
    

class PaymentAdmin(admin.ModelAdmin):
    list_display = ['item_name', 'payer_email', 'gross_amount', 'txn_id', 'created']
    
    

admin.site.register(Post, PostAdmin)

admin.site.register(Inquiry, InquiryAdmin)

admin.site.register(Payment, PaymentAdmin)