from django.contrib import admin
from .models import Post, Inquiry
from rangefilter.filters import DateRangeFilter


class PostAdmin(admin.ModelAdmin):
    list_display = ['flight_date', 'name', 'suburb', 'contact',
                    'created', 'price', 'is_confirmed', 'cancelled', 
                    'reConfirmed', 'return_flight_date', 'return_flight_number',
                     'return_flight_time' ]

    list_filter = (('flight_date', DateRangeFilter), 'suburb')

    search_fields = ['flight_date', 'pickup_time', 'suburb', 'email', 
                     'name', 'contact']


class InquiryAdmin(admin.ModelAdmin):
    list_display = ['flight_date', 'name', 'suburb', 'contact',
                    'created', 'price', 'is_confirmed', 'cancelled', 
                    'reConfirmed', 'return_flight_date', 'return_flight_number',
                     'return_flight_time' ]

    list_filter = (('flight_date', DateRangeFilter), 'suburb')

    search_fields = ['flight_date', 'pickup_time', 'suburb', 'email', 
                     'name', 'contact']

admin.site.register(Post, PostAdmin)

admin.site.register(Inquiry, InquiryAdmin)
