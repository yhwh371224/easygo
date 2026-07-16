from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.db import models
from utils.prepay_helper import is_foreign_number


class Inquiry(models.Model):
    name = models.CharField(max_length=100, blank=False)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    booker_name = models.CharField(max_length=100, blank=True, null=True)
    booker_email = models.EmailField(blank=True, null=True)
    booker_contact = models.CharField(max_length=150, blank=True, null=True)
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
    booker_contact = models.CharField(max_length=150, blank=True, null=True)
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
    driver_price = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Amount used for driver dashboard display and commission/settlement calculations. '
                   'If empty, automatically filled with the price value on save. Separate from customer payment (price/paid).',
    )
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
        help_text="Another driver collected cash directly from the customer (not company revenue, excluded from GST)",
    )
    cruise = models.BooleanField(default=False, blank=True)
    cancelled = models.BooleanField(default=False, blank=True)
    private_ride = models.BooleanField(default=False, blank=True)
    reminder = models.BooleanField(default=False, blank=True)
    sent_email = models.BooleanField(default=False, blank=True)
    sms_reminder = models.BooleanField(default=False, blank=True)
    prepay = models.BooleanField(default=False, blank=True)
    pending = models.BooleanField(default=False, blank=True)
    final_warning_at = models.DateTimeField(
        null=True, blank=True,
        help_text='48h 무응답 최종 경고 메일 발송 시각. 24h 유예 후 자동 취소 판단에 사용.',
    )
    short_payment_notified_at = models.DateTimeField(
        null=True, blank=True,
        help_text='잔액 부족(short payment) 안내 메일 발송 시각. final_notice 중복 발송 방지에 사용.',
    )
    no_payment_notice_sent_at = models.DateTimeField(
        null=True, blank=True,
        help_text='결제 미완료 1차 안내(Payment notice) 발송 시각. no_payment_yet 중복 발송 방지에 사용.',
    )
    no_payment_urgent_sent_at = models.DateTimeField(
        null=True, blank=True,
        help_text='결제 미완료 최종 안내(Urgent notice for payment) 발송 시각. no_payment_yet 중복 발송 방지에 사용.',
    )
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
        help_text='Commission % applied to this booking. Automatically set to the default when a driver is assigned.',
    )
    commission_amount_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Flat commission amount ($) for this booking only. If set, used instead of commission_rate(%).',
    )
    special_items = models.JSONField(default=dict, blank=True)
    deposit_amount_due = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Amount invoiced as a deposit. If payment received reaches this amount, '
                   'the unpaid-balance reminder email is not sent even if it falls short of the full price.',
    )
    created = models.DateTimeField(auto_now_add=True)

    @property
    def invoice_name(self):
        return self.booker_name if self.booker_name else self.name

    def save(self, *args, **kwargs):
        # Auto: check driver_collected_cash when a non-Sam driver is assigned and it's a cash booking
        # (customer paid the driver directly -> excluded from company revenue/GST). Once True,
        # leave it alone; Sam's (own) rides are excluded so they stay as company revenue.
        if (
            self.cash
            and self.driver_id
            and not self.driver_collected_cash
            and (self.driver.driver_name or '').strip().lower() != 'sam'
        ):
            self.driver_collected_cash = True
            uf = kwargs.get('update_fields')
            if uf is not None:
                kwargs['update_fields'] = set(uf) | {'driver_collected_cash'}
        # Until driver_price is manually set, it follows price minus 10.
        if not self.driver_price:
            try:
                self.driver_price = str(Decimal(str(self.price)) - Decimal('10'))
            except (InvalidOperation, TypeError):
                self.driver_price = self.price
            uf = kwargs.get('update_fields')
            if uf is not None:
                kwargs['update_fields'] = set(uf) | {'driver_price'}
        super().save(*args, **kwargs)

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
    def _driver_price_decimal(self):
        """driver_price is a CharField (may be blank/None/non-numeric) — coerce safely."""
        try:
            return Decimal(str(self.driver_price))
        except (InvalidOperation, TypeError):
            return Decimal('0')

    @property
    def commission_amount(self):
        """Company commission on this ride. A flat commission_amount_override
        takes priority; otherwise falls back to driver_price * commission_rate%."""
        if self.commission_amount_override is not None:
            return self.commission_amount_override.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if not self.commission_rate:
            return Decimal('0')
        commission = self._driver_price_decimal * self.commission_rate / Decimal('100')
        return commission.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def subcontractor_payout(self):
        """What the subcontractor is paid: driver_price − commission. Display/calc only."""
        payout = self._driver_price_decimal - self.commission_amount
        return payout.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    class Meta:
        ordering = ['-created']
