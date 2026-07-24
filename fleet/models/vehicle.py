from django.db import models


class Vehicle(models.Model):
    make_model = models.CharField(max_length=100, verbose_name='Make / Model')
    plate_number = models.CharField(max_length=20, unique=True, verbose_name='Plate number')

    registration_date = models.DateField(null=True, blank=True, verbose_name='Registration date')
    rego_expiry_date = models.DateField(null=True, blank=True, verbose_name='Rego expiry date')
    inspection_date = models.DateField(null=True, blank=True, verbose_name='Inspection expiry date')

    green_slip_provider = models.CharField(max_length=100, blank=True, verbose_name='Green slip provider')
    green_slip_cost = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Green slip cost',
    )
    green_slip_expiry_date = models.DateField(null=True, blank=True, verbose_name='Green slip expiry date')

    assigned_driver = models.ForeignKey(
        'blog.Driver', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='vehicles', verbose_name='Assigned driver',
    )
    odometer_km = models.PositiveIntegerField(null=True, blank=True, verbose_name='Current odometer (km)')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    notes = models.TextField(blank=True, verbose_name='Notes')

    class Meta:
        ordering = ['plate_number']

    def __str__(self):
        return f"{self.plate_number} ({self.make_model})"
