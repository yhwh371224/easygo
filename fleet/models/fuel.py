from django.db import models


class FuelLog(models.Model):
    """한 번의 주유. 연비는 '가득 → 가득' 구간으로 계산한다(fleet/fuel.py).

    날짜/금액만으로는 은행 기록과 같지만, 주행거리와 리터는 여기에만 있다.
    """

    SOURCE_TELEGRAM = 'telegram'
    SOURCE_ADMIN = 'admin'
    SOURCE_CHOICES = [
        (SOURCE_TELEGRAM, 'Telegram'),
        (SOURCE_ADMIN, 'Admin'),
    ]

    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='fuel_logs', verbose_name='Vehicle',
    )
    date = models.DateField(verbose_name='Date')
    odometer_km = models.PositiveIntegerField(verbose_name='Odometer (km)')
    litres = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Litres')
    amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Amount ($)')
    full_tank = models.BooleanField(default=True, verbose_name='Full tank')
    notes = models.TextField(blank=True, verbose_name='Notes')

    driver = models.ForeignKey(
        'blog.Driver', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fuel_logs', verbose_name='Logged by',
    )
    source = models.CharField(
        max_length=10, choices=SOURCE_CHOICES, default=SOURCE_ADMIN, verbose_name='Source',
    )
    bank_transaction = models.OneToOneField(
        'accounting.Transaction', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fuel_log', verbose_name='Bank transaction',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # 저장 시 fleet.fuel.refresh_stored_values() 가 채운다 — 직접 입력하지 않는다.
    # km_per_l / cost_per_km 는 '가득 → 가득' 구간이 있을 때만 값이 있다
    # (첫 기록, 가득 아님 기록은 비어 있음).
    price_per_litre = models.DecimalField(
        max_digits=6, decimal_places=3, null=True, blank=True, editable=False,
        verbose_name='$/1L',
    )
    distance_km = models.PositiveIntegerField(
        null=True, blank=True, editable=False, verbose_name='총Km',
        help_text='직전 가득 주유 이후 달린 거리',
    )
    km_per_l = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True, editable=False,
        verbose_name='km/1L',
    )
    cost_per_km = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, editable=False,
        verbose_name='$/1km',
    )

    class Meta:
        ordering = ['-date', '-odometer_km']
        verbose_name = 'Fuel Log'
        verbose_name_plural = 'Fuel Logs'

    def __str__(self):
        return f"{self.vehicle.plate_number} {self.date} {self.odometer_km}km {self.litres}L"

