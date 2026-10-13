from django.contrib import admin
from django.db import transaction

from .models import Vehicle, ServiceVisit, ServiceItem


class ServiceVisitInline(admin.TabularInline):
    model = ServiceVisit
    extra = 0
    fields = ('service_date', 'self_serviced', 'vendor', 'total_cost', 'odometer_km')
    show_change_link = True
    can_delete = False


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        'plate_number', 'make_model', 'assigned_driver', 'is_active',
        'rego_expiry_date', 'inspection_date', 'green_slip_expiry_date',
    )
    list_filter = ('is_active', 'assigned_driver')
    search_fields = ('plate_number', 'make_model')
    inlines = [ServiceVisitInline]


class ServiceItemInline(admin.TabularInline):
    model = ServiceItem
    extra = 1
    fields = ('service_type', 'product_name', 'part_number', 'cost')


@admin.register(ServiceVisit)
class ServiceVisitAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'service_date', 'self_serviced', 'vendor', 'total_cost', 'odometer_km')
    list_filter = ('self_serviced', 'vehicle')
    date_hierarchy = 'service_date'
    search_fields = ('vehicle__plate_number', 'vendor')
    inlines = [ServiceItemInline]
    actions = ['duplicate_visits']

    @admin.action(description='Duplicate selected service visits')
    def duplicate_visits(self, request, queryset):
        count = 0
        with transaction.atomic():
            for visit in queryset.prefetch_related('items'):
                items = list(visit.items.all())
                visit.pk = None
                visit._state.adding = True
                visit.save()
                for item in items:
                    item.pk = None
                    item._state.adding = True
                    item.visit = visit
                ServiceItem.objects.bulk_create(items)
                count += 1
        self.message_user(request, f'{count} service visit(s) duplicated.')
