import secrets
from decimal import Decimal

from django.core.validators import FileExtensionValidator
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from blog.storage import private_driver_docs_storage

LICENSE_CLASS_CHOICES = [
    ('C', 'Car (C)'),
    ('LR', 'Light Rigid (LR)'),
    ('MR', 'Medium Rigid (MR)'),
    ('HR', 'Heavy Rigid (HR)'),
    ('HC', 'Heavy Combination (HC)'),
    ('MC', 'Multi Combination (MC)'),
    ('OTHER', 'Other'),
]

PAYMENT_METHOD_CHOICES = [
    ('bank', 'Bank Transfer'),
    ('payid', 'PayID'),
]


class VirtualNumber(models.Model):
    number = models.CharField(max_length=20, unique=True)

    # Bird channel that owns this number, one per platform. Populated by
    # `manage.py sync_bird_channels`; a number is useless to us until Bird is
    # routing its calls and texts at our webhooks, hence is_wired below.
    sms_channel_id = models.CharField(
        max_length=64, blank=True, null=True, unique=True,
        help_text='Bird sms-messagebird channel id. Run sync_bird_channels to fill.',
    )
    voice_channel_id = models.CharField(
        max_length=64, blank=True, null=True, unique=True,
        help_text='Bird voice-messagebird channel id. Run sync_bird_channels to fill.',
    )

    @property
    def is_wired(self):
        """Whether Bird actually delivers this number's traffic to us.

        Assigning a number in the admin is not enough: without both channels
        synced, a customer dialling it reaches nothing. Never advertise a
        number that isn't wired.
        """
        return bool(self.sms_channel_id and self.voice_channel_id)

    def __str__(self):
        suffix = '' if self.is_wired else ' (not wired)'
        return f'{self.number}{suffix}'


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
    payment_match_digits = models.CharField(max_length=30, blank=True, null=True,
        help_text='PayID 번호 또는 계좌번호 끝자리 등 송금 식별 숫자. 비워두면 숫자 매칭 안 함.')
    is_active = models.BooleanField(default=True)
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
    # Self-declared on the public application form — NOT proof of cover.
    # Staff still sight the certificate of currency before flipping is_active.
    has_vehicle_insurance = models.BooleanField(
        default=False,
        help_text='차량 보험(대인/대물 등) 가입 여부. 지원서에서 본인이 체크한 값이며 '
                   '증빙 서류 확인은 별도로 해야 함.',
    )
    driver_bankdetails = models.TextField(blank=True, null=True)

    license_number = models.CharField(max_length=40, blank=True, null=True)
    license_class = models.CharField(
        max_length=10, choices=LICENSE_CLASS_CHOICES, blank=True, null=True,
    )
    license_scan = models.FileField(
        upload_to='driver_licenses/%Y/%m/',
        storage=private_driver_docs_storage,
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'pdf'])],
        help_text='드라이버 라이센스 스캔/사진. 오피스 관리자만 열람 가능 (private storage).',
    )

    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True,
    )
    bank_account_name = models.CharField(max_length=100, blank=True, null=True)
    bank_bsb = models.CharField(max_length=10, blank=True, null=True)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)
    payid_number = models.CharField(max_length=50, blank=True, null=True)

    # Set when a driver self-registers via the public application form.
    # Paired with is_active=False at creation — staff flips is_active to True
    # in the admin once licence/insurance docs have been checked. Null for
    # drivers office staff created directly (no application to review).
    application_submitted_at = models.DateTimeField(null=True, blank=True)
    google_calendar_id = models.CharField(max_length=255, blank=True, null=True)
    virtual_number = models.ForeignKey('VirtualNumber', on_delete=models.SET_NULL, null=True, blank=True)
    agreement_token = models.CharField(
        max_length=64, unique=True, null=True, blank=True, editable=False,
        help_text='로그인 없이 subcontractor agreement 페이지를 열 수 있는 토큰. '
                   '자동 생성됨.',
    )
    is_company = models.BooleanField(
        default=False,
        help_text='이 레코드가 개인 드라이버가 아니라 드라이버를 공급하는 협력업체(법인)인 '
                   '경우 체크. Agreement 페이지 문구가 회사용으로 바뀌고, 확인은 그 회사 '
                   '담당자 이름/직책으로 기록됨.',
    )

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        if not self.agreement_token:
            self.agreement_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.driver_name


# Bump this when the agreement wording changes. Drivers are asked to
# re-confirm whenever the current version differs from what they last signed.
CURRENT_AGREEMENT_VERSION = "2026-07"


class DriverAgreement(models.Model):
    """A driver's acknowledgement of the subcontractor agreement.

    Purely a record of consent — deliberately isolated from the accounting
    app (no Transaction / PayrollEntry writes ever happen off this model).
    """
    driver = models.ForeignKey(
        'Driver',
        on_delete=models.CASCADE,
        related_name='agreements',
    )
    version = models.CharField(max_length=20, default=CURRENT_AGREEMENT_VERSION)

    item_status_confirmed = models.BooleanField(default=False)
    item_liability_confirmed = models.BooleanField(default=False)
    item_rcti_confirmed = models.BooleanField(default=False)
    item_tax_invoice_confirmed = models.BooleanField(default=False)

    # Only populated for company-level agreements (driver.is_company) — the
    # name/title of the person at the partner company who certified it, since
    # the company itself can't click a button.
    signed_by_name = models.CharField(max_length=100, blank=True, null=True)
    signed_by_title = models.CharField(max_length=100, blank=True, null=True)

    confirmed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)

    # Snapshot of driver.gst_registered at the moment of confirmation, so the
    # record is meaningful even if the driver's GST status later changes.
    gst_registered_snapshot = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # One acknowledgement row per driver per version.
        unique_together = ('driver', 'version')

    def __str__(self):
        state = 'confirmed' if self.confirmed_at else 'pending'
        return f"{self.driver} | {self.version} | {state}"


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
