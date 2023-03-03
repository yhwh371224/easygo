from django.contrib import admin
from .models import Point
from rangefilter.filters import DateRangeFilter


class PointAdmin(admin.ModelAdmin):
    list_display = ['date', 'contact', 'email', 'startpoint', 'endpoint', 'pickuptime', 
                    'passenger', 'created']

    search_fields = ['date', 'pickuptime', 'startpoint',
                     'endpoint', 'name', 'contact']


admin.site.register(Point, PointAdmin)

