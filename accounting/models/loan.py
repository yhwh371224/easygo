from decimal import Decimal

from django.db import models
from django.db.models import Sum


class DirectorLoan(models.Model):
    """Director's loan / capital contribution tracking.

    Records money the director injects into (contribution) or withdraws from
    (repayment) the company as a personal loan.  These are balance-sheet
    liabilities — they must never appear in P&L or BAS reports.
    """

    DIRECTION_CHOICES = [
        ('contribution', 'Contribution (Director → Company)'),
        ('repayment',    'Repayment (Company → Director)'),
    ]

    date        = models.DateField()
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    direction   = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['date', 'pk']
        verbose_name = "Director's Loan"
        verbose_name_plural = "Director's Loans"

    def __str__(self):
        return f"{self.date} {self.get_direction_display()} ${self.amount}"

    @classmethod
    def current_balance(cls):
        """Outstanding balance = contributions − repayments.

        Positive → company still owes the director.
        Zero / negative → director has been fully repaid (or over-repaid).
        """
        agg = cls.objects.values('direction').annotate(total=Sum('amount'))
        totals = {row['direction']: row['total'] for row in agg}
        contributions = totals.get('contribution') or Decimal('0')
        repayments    = totals.get('repayment')    or Decimal('0')
        return contributions - repayments
