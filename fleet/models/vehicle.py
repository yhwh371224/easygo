from django.db import models


class Vehicle(models.Model):
    make_model = models.CharField(max_length=100, verbose_name='차종류')
    plate_number = models.CharField(max_length=20, unique=True, verbose_name='차번호')

    registration_date = models.DateField(null=True, blank=True, verbose_name='등록일')
    rego_expiry_date = models.DateField(null=True, blank=True, verbose_name='Rego 만료일')
    inspection_date = models.DateField(null=True, blank=True, verbose_name='Inspection 만료일')

    green_slip_provider = models.CharField(max_length=100, blank=True, verbose_name='Green slip 업체')
    green_slip_cost = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Green slip 비용',
    )
    green_slip_expiry_date = models.DateField(null=True, blank=True, verbose_name='Green slip 만료일')

    assigned_driver = models.ForeignKey(
        'blog.Driver', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='vehicles', verbose_name='담당 기사',
    )
    odometer_km = models.PositiveIntegerField(null=True, blank=True, verbose_name='현재 주행거리(km)')
    is_active = models.BooleanField(default=True, verbose_name='운행중')
    notes = models.TextField(blank=True, verbose_name='메모')

    class Meta:
        ordering = ['plate_number']

    def __str__(self):
        return f"{self.plate_number} ({self.make_model})"
