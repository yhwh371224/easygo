from django.contrib import admin
from django.db import transaction

from .fuel import economy_for, match_bank_transactions, refresh_stored_values
from .models import Vehicle, ServiceVisit, ServiceItem, FuelLog


class FuelLogInline(admin.TabularInline):
    model = FuelLog
    extra = 0
    fields = ('date', 'odometer_km', 'litres', 'amount', 'full_tank',
              'price_per_litre', 'km_per_l', 'cost_per_km', 'notes')
    readonly_fields = ('price_per_litre', 'km_per_l', 'cost_per_km')
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
        'date', 'vehicle', 'odometer_km', 'litres', 'amount', 'price_per_litre',
        'full_tank', 'distance', 'km_per_l', 'l_per_100km', 'cost_per_km', 'driver', 'bank_matched',
    )
    list_filter = ('vehicle', 'full_tank', 'source')
    date_hierarchy = 'date'
    search_fields = ('vehicle__plate_number', 'notes')
    raw_id_fields = ('bank_transaction',)
    readonly_fields = ('price_per_litre', 'km_per_l', 'cost_per_km', 'source', 'created_at')
    fields = (
        'vehicle', 'date', 'odometer_km', 'litres', 'amount', 'full_tank', 'notes',
        'price_per_litre', 'km_per_l', 'cost_per_km',
        'driver', 'bank_transaction', 'source', 'created_at',
    )
    actions = ['match_bank']

    def _eco(self, obj):
        cache = getattr(self, '_eco_cache', None)
        if cache is None:
            cache = self._eco_cache = {}
        if obj.pk not in cache:
            cache[obj.pk] = economy_for(obj)
        return cache[obj.pk]

    def changelist_view(self, request, extra_context=None):
        self._eco_cache = {}
        return super().changelist_view(request, extra_context)

    @admin.display(description='km')
    def distance(self, obj):
        eco = self._eco(obj)
        return eco['distance_km'] if eco else '—'

    @admin.display(description='L/100km')
    def l_per_100km(self, obj):
        eco = self._eco(obj)
        return eco['l_per_100km'] if eco else '—'

    @admin.display(description='Bank', boolean=True)
    def bank_matched(self, obj):
        return obj.bank_transaction_id is not None

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

    @admin.action(description='Match selected with bank fuel transactions')
    def match_bank(self, request, queryset):
        n = match_bank_transactions(queryset.filter(bank_transaction__isnull=True))
        self.message_user(request, f'{n} fuel log(s) matched to bank transactions.')
