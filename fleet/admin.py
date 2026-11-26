from django.contrib import admin
from django.db import transaction

from .fuel import match_bank_transactions, refresh_stored_values
from .models import Vehicle, ServiceVisit, ServiceItem, FuelLog


class FuelLogInline(admin.TabularInline):
    model = FuelLog
    extra = 0
    fields = ('date', 'distance_km', 'odometer_km', 'litres', 'amount',
              'price_per_litre', 'km_per_l', 'cost_per_km', 'notes')
    readonly_fields = ('distance_km', 'price_per_litre', 'km_per_l', 'cost_per_km')
    show_change_link = True
    can_delete = False

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-odometer_km')


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
    inlines = [ServiceVisitInline, FuelLogInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # 인라인에서 주유 기록을 고쳤을 수 있으니 저장 값($/L, km/L, $/km)을 다시 맞춘다.
        refresh_stored_values(form.instance.pk)


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


@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'distance_col', 'odometer_col', 'litres', 'amount_col',
        'price_col', 'km_per_l_col', 'cost_per_km_col',
    )
    list_filter = ('vehicle', 'source')
    date_hierarchy = 'date'
    search_fields = ('vehicle__plate_number', 'notes')
    readonly_fields = ('distance_km', 'price_per_litre', 'km_per_l', 'cost_per_km', 'source', 'created_at')
    fields = (
        'vehicle', 'date', 'odometer_km', 'litres', 'amount', 'notes',
        'distance_km', 'price_per_litre', 'km_per_l', 'cost_per_km',
        'source', 'created_at',
    )

    # 목록 머리글 이름. (Admin CSS 가 머리글을 대문자로 보여준다.)
    @admin.display(description='총Km', ordering='distance_km')
    def distance_col(self, obj):
        return obj.distance_km if obj.distance_km is not None else '—'

    @admin.display(description='Odometer', ordering='odometer_km')
    def odometer_col(self, obj):
        return obj.odometer_km

    @admin.display(description='Amount', ordering='amount')
    def amount_col(self, obj):
        return obj.amount

    @admin.display(description='$/1L', ordering='price_per_litre')
    def price_col(self, obj):
        return obj.price_per_litre if obj.price_per_litre is not None else '—'

    @admin.display(description='km/1L', ordering='km_per_l')
    def km_per_l_col(self, obj):
        return obj.km_per_l if obj.km_per_l is not None else '—'

    @admin.display(description='$/1km', ordering='cost_per_km')
    def cost_per_km_col(self, obj):
        return obj.cost_per_km if obj.cost_per_km is not None else '—'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        vehicle = obj.vehicle
        if vehicle.odometer_km is None or obj.odometer_km > vehicle.odometer_km:
            Vehicle.objects.filter(pk=vehicle.pk).update(odometer_km=obj.odometer_km)
        refresh_stored_values(vehicle.pk)
        if obj.bank_transaction_id is None:
            match_bank_transactions([obj])

    def delete_model(self, request, obj):
        vehicle_id = obj.vehicle_id
        super().delete_model(request, obj)
        refresh_stored_values(vehicle_id)

    def delete_queryset(self, request, queryset):
        vehicle_ids = set(queryset.values_list('vehicle_id', flat=True))
        super().delete_queryset(request, queryset)
        for vehicle_id in vehicle_ids:
            refresh_stored_values(vehicle_id)
