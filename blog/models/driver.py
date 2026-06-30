from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class VirtualNumber(models.Model):
    number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.number


class Driver(models.Model):
    order = models.PositiveSmallIntegerField(default=0)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    must_change_password = models.BooleanField(default=True)
    region = models.ForeignKey('regions.Region', null=True, blank=True, on_delete=models.SET_NULL)
    is_default = models.BooleanField(default=False)
    driver_name = models.CharField(max_length=100, blank=True, null=True)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    abn = models.CharField(max_length=20, blank=True, null=True)
    gst_registered = models.BooleanField(default=False)
    commission_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0'),
        help_text='회사 커미션 %. 예: 10.00 = 10%',
    )
    driver_contact = models.CharField(max_length=50, blank=True, null=True)
    driver_email = models.EmailField(blank=True, null=True)
    driver_address = models.CharField(max_length=200, blank=True, null=True)
    driver_plate = models.CharField(max_length=30, blank=True, null=True)
    driver_car = models.CharField(max_length=30, blank=True, null=True)
    driver_bankdetails = models.TextField(blank=True, null=True)
    google_calendar_id = models.CharField(max_length=255, blank=True, null=True)
    virtual_number = models.ForeignKey('VirtualNumber', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.driver_name


class DriverSettlement(models.Model):
    driver = models.ForeignKey(
        'Driver',
        on_delete=models.CASCADE,
        related_name='settlements'
    )

    # Settlement ID (RCTI / Xero / audit 핵심)
    settlement_number = models.CharField(max_length=60, unique=True, db_index=True)
    # 예: SYD-JSMITH-260602-SET-01

    # 기간 (핵심)
    from_date = models.DateField()
    to_date = models.DateField()

    # money breakdown (Xero export 핵심)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cash_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # status flow (중요)
    STATUS_CHOICES = [
        ('draft', 'Draft'),        # 계산 중
        ('locked', 'Locked'),      # 확정 (수정 불가)
        ('paid', 'Paid'),          # PayID 송금 완료
        ('exported', 'Exported'),  # Xero 전송 완료
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # payment info
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('payid', 'PayID'),
            ('bank', 'Bank Transfer'),
        ],
        default='payid'
    )

    paid_at = models.DateTimeField(null=True, blank=True)

    # Xero export tracking
    xero_exported = models.BooleanField(default=False)
    xero_exported_at = models.DateTimeField(null=True, blank=True)
    xero_reference = models.CharField(max_length=100, null=True, blank=True)
    xero_invoice_id = models.CharField(max_length=100, null=True, blank=True)

    # audit
    settled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(default=timezone.now)

    @property
    def rcti_number(self):
        return self.settlement_number

    class Meta:
        ordering = ['-settled_at']

    def __str__(self):
        return f"{self.settlement_number} | {self.driver} | ${self.total_amount}"
    

class DriverSettlementItem(models.Model):
    settlement = models.ForeignKey('DriverSettlement', on_delete=models.CASCADE, related_name='items', db_index=True)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, db_index=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('settlement', 'post')





# class DriverSettlement(models.Model):
#     driver = models.ForeignKey('Driver', on_delete=models.CASCADE, related_name='settlements')
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     note = models.TextField(blank=True, null=True)
#     settled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
#     settled_at = models.DateTimeField(default=timezone.now)

#     class Meta:
#         ordering = ['-settled_at']

#     @property
#     def local_date(self):
#         import pytz
#         from django.utils.timezone import localtime
#         try:
#             tz = pytz.timezone(self.driver.region.timezone)
#             return self.settled_at.astimezone(tz).date()
#         except Exception:
#             return localtime(self.settled_at).date()

#     def __str__(self):
#         return f"{self.driver} - ${self.amount} on {self.local_date}"
