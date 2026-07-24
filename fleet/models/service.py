from django.db import models


class ServiceVisit(models.Model):
    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='service_visits', verbose_name='Vehicle',
    )
    service_date = models.DateField(verbose_name='Service date')
    self_serviced = models.BooleanField(default=False, verbose_name='Self serviced')
    vendor = models.CharField(max_length=100, blank=True, verbose_name='Vendor')
    odometer_km = models.PositiveIntegerField(null=True, blank=True, verbose_name='Odometer at service (km)')
    total_cost = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Total cost',
    )
    receipt_photo = models.ImageField(
        upload_to='fleet/receipts/%Y/%m/', null=True, blank=True, verbose_name='Receipt photo',
    )
    notes = models.TextField(blank=True, verbose_name='Notes')

    class Meta:
        ordering = ['-service_date', '-pk']
        verbose_name = 'Service Visit'
        verbose_name_plural = 'Service Visits'

    def __str__(self):
        who = 'Self serviced' if self.self_serviced else (self.vendor or 'Vendor')
        return f"{self.vehicle.plate_number} {self.service_date} ({who})"


class ServiceItem(models.Model):
    ENGINE_OIL = 'engine_oil'
    OIL_FILTER = 'oil_filter'
    AIR_FILTER = 'air_filter'
    TYRE = 'tyre'
    BRAKE_PAD = 'brake_pad'
    TRANSMISSION_OIL = 'transmission_oil'
    OTHER = 'other'

    SERVICE_TYPE_CHOICES = [
        (ENGINE_OIL, 'Engine oil'),
        (OIL_FILTER, 'Oil filter'),
        (AIR_FILTER, 'Air filter'),
        (TYRE, 'Tyre'),
        (BRAKE_PAD, 'Brake pad'),
        (TRANSMISSION_OIL, 'Transmission oil'),
        (OTHER, 'Other'),
    ]

    visit = models.ForeignKey(
        'fleet.ServiceVisit', on_delete=models.CASCADE, related_name='items', verbose_name='Visit',
    )
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, verbose_name='Item')
    product_name = models.CharField(max_length=100, blank=True, verbose_name='Product name')
    part_number = models.CharField(max_length=100, blank=True, verbose_name='Part number')
    cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Cost')

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return f"{self.get_service_type_display()} - {self.product_name or self.part_number or ''}".strip(' -')
