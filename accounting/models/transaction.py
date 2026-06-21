from django.db import models


class Transaction(models.Model):
    """Manual / catch-all financial entries that existing models don't capture.

    Sales, customer payments and driver subcontracting are recorded by the blog
    app (Post / PaypalPayment / StripePayment / DriverSettlement) — do NOT
    duplicate those here. This model is for everything else (bank fees, fuel,
    refunds, manual adjustments, etc.).
    """

    DIRECTION_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    BRAND_CHOICES = [
        ('shuttle', 'Shuttle'),
        ('coaches', 'Coaches'),
    ]

    GST_CODE_CHOICES = [
        ('gst', 'GST'),
        ('gst_free', 'GST Free'),
        ('no_gst', 'No GST'),
    ]

    SOURCE_CHOICES = [
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('manual', 'Manual'),
    ]

    date = models.DateField()
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    brand = models.CharField(max_length=10, choices=BRAND_CHOICES, default='shuttle')
    description = models.CharField(max_length=255)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    gst_code = models.CharField(max_length=10, choices=GST_CODE_CHOICES, default='no_gst')
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    category = models.CharField(max_length=50)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual')
    counterparty = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    import_hash = models.CharField(
        max_length=64, blank=True, default='', db_index=True,
        help_text="SHA-256 fingerprint of the source bank row (dedup key). "
                  "Empty for manually-entered transactions.",
    )
    gst_auto_estimated = models.BooleanField(
        default=False,
        help_text="True if gst_code/gst_amount were auto-guessed on import "
                  "and still need human review before BAS.",
    )
    needs_review = models.BooleanField(
        default=False, db_index=True,
        help_text="Held for human triage (e.g. a large bank withdrawal). "
                  "Excluded from BAS 1B and P&L totals until approved.",
    )
    excluded = models.BooleanField(
        default=False, db_index=True,
        help_text="Permanently excluded from BAS/P&L — e.g. a driver payout "
                  "already recorded via DriverSettlement (avoids double count).",
    )

    class Meta:
        indexes = [
            models.Index(fields=['date', 'brand', 'direction']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['import_hash'],
                condition=models.Q(import_hash__gt=''),
                name='uniq_bank_import_hash',
            ),
        ]

    def __str__(self):
        return f"{self.date} {self.direction} {self.gross_amount} ({self.brand})"
