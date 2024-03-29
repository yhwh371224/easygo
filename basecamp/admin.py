from django.contrib import admin
from .models import Inquiry_point
from rangefilter.filters import DateRangeFilter
from blog.admin import admin_site


class InquiryPointAdmin(admin.ModelAdmin):
    list_display = ['flight_date', 'contact', 'email', 'flight_number', 'street', 'pickup_time', 
                    'no_of_passenger', 'created']

    search_fields = ['flight_date', 'pickup_time', 'flight_number',
                     'street', 'name', 'contact']
    

admin_site.register(Inquiry_point, InquiryPointAdmin)
admin.site.register(Inquiry_point, InquiryPointAdmin)


