from django.db import models


class PaypalPayment(models.Model):
    """One verified PayPal IPN event.

    Not every row is money coming in: a refund, a dispute reversal and the
    cancellation of a dispute all arrive as IPNs too. ``kind`` tells them apart
    from the stored IPN metadata — see the field block below.
    """

    KIND_PAYMENT = 'payment'
    KIND_REFUND = 'refund'
    KIND_DISPUTE = 'dispute'
    KIND_DISPUTE_RESOLVED = 'dispute_resolved'

    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    txn_id = models.CharField(max_length=100, blank=True, null=True)
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    # --- IPN metadata (added 2026-08) -------------------------------------
    # Before these existed only the sign of ``amount`` was known, so a customer
    # dispute (money pulled back while the case is open) looked exactly like a
    # refund we had issued — the customer got a "Refund Processed" email for a
    # dispute that was still open. Storing the payload lets kind() tell them
    # apart, and ``raw`` keeps the whole thing for later forensics.
    payment_status = models.CharField(
        max_length=30, blank=True, default='',
        help_text="IPN payment_status: Completed / Refunded / Reversed / "
                  "Canceled_Reversal … Blank on rows created before 2026-08.",
    )
    txn_type = models.CharField(max_length=50, blank=True, default='')
    parent_txn_id = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Original transaction a refund/reversal relates to.",
    )
    reason_code = models.CharField(max_length=50, blank=True, default='')
    case_id = models.CharField(
        max_length=64, blank=True, default='', db_index=True,
        help_text="PayPal dispute/claim case id (PP-R-...), when the IPN is a "
                  "case notification.",
    )
    case_type = models.CharField(max_length=30, blank=True, default='')
    raw = models.JSONField(
        blank=True, null=True,
        help_text="Full verified IPN payload as received.",
    )

    class Meta:
        ordering = ['-created']

    def __str__(self):
        status = "Done" if self.is_processed else "Pending"
        return f"{self.name} - {self.amount} ({status})"

    @property
    def kind(self):
        """Classify the IPN: payment / refund / dispute / dispute_resolved.

        Rows written before the metadata fields existed carry none of it, so
        they fall back to the sign of the amount — exactly how every IPN was
        classified before, which keeps historical rows behaving as they did.
        """
        status = (self.payment_status or '').strip().lower()
        txn_type = (self.txn_type or '').strip().lower()

        if status == 'canceled_reversal':
            return self.KIND_DISPUTE_RESOLVED
        if status == 'reversed' or txn_type in ('new_case', 'adjustment') or self.case_id:
            return self.KIND_DISPUTE
        if status == 'refunded' or txn_type == 'refund':
            return self.KIND_REFUND

        return self.KIND_REFUND if (self.amount or 0) < 0 else self.KIND_PAYMENT


class StripePayment(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_intent_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.name} - {self.amount} ({'Done' if self.is_processed else 'Pending'})"
