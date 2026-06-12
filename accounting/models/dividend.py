from django.db import models


class DividendRecord(models.Model):
    """Dividend retention / franking credit tracking.

    Standalone model — not derived from any existing model.
    """

    STATUS_CHOICES = [
        ('retained', 'Retained'),
        ('paid', 'Paid'),
    ]

    declared_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    franking_credit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='retained')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.declared_date} {self.amount} ({self.status})"
