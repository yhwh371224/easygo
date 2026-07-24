from django.db import models


class ServiceVisit(models.Model):
    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='service_visits', verbose_name='차량',
    )
    service_date = models.DateField(verbose_name='서비스 날짜')
    self_serviced = models.BooleanField(default=False, verbose_name='자가정비')
    vendor = models.CharField(max_length=100, blank=True, verbose_name='업체명')
    odometer_km = models.PositiveIntegerField(null=True, blank=True, verbose_name='당시 주행거리(km)')
    total_cost = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='총 비용',
    )
    receipt_photo = models.ImageField(
        upload_to='fleet/receipts/%Y/%m/', null=True, blank=True, verbose_name='영수증 사진',
    )
    notes = models.TextField(blank=True, verbose_name='메모')

    class Meta:
        ordering = ['-service_date', '-pk']
        verbose_name = 'Service Visit'
        verbose_name_plural = 'Service Visits'

    def __str__(self):
        who = '자가정비' if self.self_serviced else (self.vendor or '업체')
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
        (ENGINE_OIL, '엔진오일'),
        (OIL_FILTER, '엔진오일필터'),
        (AIR_FILTER, '에어필터'),
        (TYRE, '타이어'),
        (BRAKE_PAD, '브레이크패드'),
        (TRANSMISSION_OIL, '트랜스미션오일'),
        (OTHER, '기타'),
    ]

    visit = models.ForeignKey(
        'fleet.ServiceVisit', on_delete=models.CASCADE, related_name='items', verbose_name='방문',
    )
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, verbose_name='항목')
    product_name = models.CharField(max_length=100, blank=True, verbose_name='제품명')
    part_number = models.CharField(max_length=100, blank=True, verbose_name='제품번호')
    cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='비용')

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return f"{self.get_service_type_display()} - {self.product_name or self.part_number or ''}".strip(' -')
