from django.db import models

from .transaction import Transaction


class PaymentFeeLog(models.Model):
    """Raw per-payment PayPal/Stripe fee entries, written the moment a
    payment settles.

    Kept out of accounting.Transaction so the day-to-day transaction list
    doesn't fill up with dozens of $2-15 fee rows. Once a month,
    compact_payment_fees rolls the previous month's rows here into one
    summary Transaction row per source, then deletes the rows it merged.
    """

    SOURCE_CHOICES = [
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
    ]

    date = models.DateField()
    direction = models.CharField(max_length=10, choices=Transaction.DIRECTION_CHOICES)
    brand = models.CharField(max_length=10, choices=Transaction.BRAND_CHOICES, default='shuttle')
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    description = models.CharField(max_length=255, db_index=True)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    gst_code = models.CharField(max_length=10, choices=Transaction.GST_CODE_CHOICES, default='no_gst')
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    counterparty = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['source', 'date']),
        ]

    def __str__(self):
        return f"{self.date} {self.source} {self.gross_amount} ({self.description})"
