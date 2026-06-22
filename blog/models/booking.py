from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.db import models
from utils.prepay_helper import is_foreign_number


class Inquiry(models.Model):
    name = models.CharField(max_length=100, blank=False)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    booker_name = models.CharField(max_length=100, blank=True, null=True)
    booker_email = models.EmailField(blank=True, null=True)
    contact = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(blank=False, db_index=True)
    email1 = models.EmailField(blank=True, null=True)
    pickup_date = models.DateField(verbose_name='pickup_date', blank=False, null=True)
    flight_number = models.CharField(max_length=100, blank=True, null=True)
    flight_time = models.CharField(max_length=30, blank=True, null=True)
    pickup_time = models.CharField(max_length=30, blank=True, null=True)
    direction = models.CharField(max_length=100, blank=True, null=True)
    suburb = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=200, blank=True, null=True)
    start_point = models.CharField(max_length=200, blank=True, null=True)
    end_point = models.CharField(max_length=200, blank=True, null=True)
    no_of_passenger = models.CharField(max_length=30, blank=False)
    no_of_baggage = models.CharField(max_length=200, blank=True, null=True)
    return_direction = models.CharField(max_length=100, blank=True, null=True)
    return_pickup_date = models.DateField(blank=True, null=True)
    return_flight_number = models.CharField(max_length=200, blank=True, null=True)
    return_flight_time = models.CharField(max_length=30, blank=True, null=True)
    return_pickup_time = models.CharField(max_length=30, blank=True, null=True)
    return_start_point = models.CharField(max_length=200, blank=True, null=True)
    return_end_point = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    notice = models.TextField(blank=True, null=True)
    price = models.CharField(max_length=100, blank=True, null=True)
    paid = models.CharField(max_length=100, blank=True, null=True)
    discount = models.CharField(max_length=30, blank=True, null=True)
    toll = models.CharField(max_length=30, blank=True, null=True)
    surcharge = models.CharField(max_length=30, blank=True, null=True)
    driver = models.ForeignKey('Driver', on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(
        'regions.Region',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='inquiries',
        default=None,
    )
    customer_history = models.CharField(max_length=100, blank=True, null=True)
    is_confirmed = models.BooleanField(default=False, blank=True)
    cash = models.BooleanField(default=False, blank=True)
    cruise = models.BooleanField(default=False, blank=True)
    cancelled = models.BooleanField(default=False, blank=True)
    private_ride = models.BooleanField(default=False, blank=True)
    reminder = models.BooleanField(default=False, blank=True)
    sent_email = models.BooleanField(default=False, blank=True)
    sms_reminder = models.BooleanField(default=False, blank=True)
    prepay = models.BooleanField(default=False, blank=True)
    pending = models.BooleanField(default=False, blank=True)
    calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    extra_stop           = models.PositiveSmallIntegerField(default=0)
    extra_stop_addresses = models.JSONField(default=list, blank=True)
    same_extra_stop      = models.BooleanField(default=False)
    special_items = models.JSONField(default=dict, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']


class Post(models.Model):
    name = models.CharField(max_length=100, blank=False)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    booker_name = models.CharField(max_length=100, blank=True, null=True)
    booker_email = models.EmailField(blank=True, null=True)
    contact = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(blank=False, db_index=True, verbose_name='email')
    email1 = models.EmailField(blank=True, null=True)
    pickup_date = models.DateField(verbose_name='pickup_date', blank=False, null=True)
    flight_number = models.CharField(max_length=100, blank=True, null=True)
    flight_time = models.CharField(max_length=30, blank=True, null=True)
    pickup_time = models.CharField(max_length=30, blank=True, null=True)
    direction = models.CharField(max_length=100, blank=True, null=True)
    suburb = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=200, blank=True, null=True)
    start_point = models.CharField(max_length=200, blank=True, null=True)
    end_point = models.CharField(max_length=200, blank=True, null=True)
    no_of_passenger = models.CharField(max_length=30, blank=False)
    no_of_baggage = models.CharField(max_length=200, blank=True, null=True)
    return_direction = models.CharField(max_length=100, blank=True, null=True)
    return_pickup_date = models.DateField(blank=True, null=True)
    return_flight_number = models.CharField(max_length=200, blank=True, null=True)
    return_flight_time = models.CharField(max_length=30, blank=True, null=True)
    return_pickup_time = models.CharField(max_length=30, blank=True, null=True)
    return_start_point = models.CharField(max_length=200, blank=True, null=True)
    return_end_point = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    notice = models.TextField(blank=True, null=True)
    price = models.CharField(max_length=100, blank=True, null=True)
    paid = models.CharField(max_length=100, blank=True, null=True)
    discount = models.CharField(max_length=30, blank=True, null=True)
    toll = models.CharField(max_length=30, blank=True, null=True)
    surcharge = models.CharField(max_length=30, blank=True, null=True)
    driver = models.ForeignKey('Driver', on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(
        'regions.Region',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='posts',
        default=None,
    )
    customer_history = models.CharField(max_length=100, blank=True, null=True)
    terminal_pickup_point = models.ForeignKey(
        'regions.TerminalPickupPoint',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
    )
    is_confirmed = models.BooleanField(default=False, blank=True)
    cash = models.BooleanField(default=False, blank=True)
    driver_collected_cash = models.BooleanField(
        default=False, blank=True,
        help_text="타 드라이버가 손님에게 직접 현금 수령 (회사 매출 아님, GST 제외)",
    )
    cruise = models.BooleanField(default=False, blank=True)
    cancelled = models.BooleanField(default=False, blank=True)
    private_ride = models.BooleanField(default=False, blank=True)
    reminder = models.BooleanField(default=False, blank=True)
    sent_email = models.BooleanField(default=False, blank=True)
    sms_reminder = models.BooleanField(default=False, blank=True)
    prepay = models.BooleanField(default=False, blank=True)
    pending = models.BooleanField(default=False, blank=True)
    calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    driver_calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    use_proxy = models.BooleanField(default=False)
    extra_stop           = models.PositiveSmallIntegerField(default=0)
    extra_stop_addresses = models.JSONField(default=list, blank=True)
    same_extra_stop      = models.BooleanField(default=False)
    commission_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0'),
        help_text='이 부킹에 적용된 커미션 %. 드라이버 배정 시 기본값 자동 적용.',
    )
    special_items = models.JSONField(default=dict, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    @property
    def invoice_name(self):
        return self.booker_name if self.booker_name else self.name

    @property
    def is_foreign_contact(self):
        return is_foreign_number(self.contact)

    @property
    def _price_decimal(self):
        """price is a CharField (may be blank/None/non-numeric) — coerce safely."""
        try:
            return Decimal(str(self.price))
        except (InvalidOperation, TypeError):
            return Decimal('0')

    @property
    def commission_amount(self):
        """Company commission on this ride. Uses Post's own commission_rate field."""
        if not self.commission_rate:
            return Decimal('0')
        commission = self._price_decimal * self.commission_rate / Decimal('100')
        return commission.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def subcontractor_payout(self):
        """What the subcontractor is paid: price − commission. Display/calc only."""
        payout = self._price_decimal - self.commission_amount
        return payout.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    class Meta:
        ordering = ['-created']
