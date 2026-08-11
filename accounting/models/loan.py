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
    source_transaction = models.OneToOneField(
        'accounting.Transaction', null=True, blank=True,
        on_delete=models.CASCADE, related_name='director_loan_entry',
        help_text="Set when this entry was derived from a personal expense paid "
                  "off the company account; empty for hand-entered loan movements. "
                  "Doubles as the idempotency key — the OneToOne guarantees at most "
                  "one loan entry per transaction, so a re-import or a repeated "
                  "admin action can never double-count the balance.",
    )

    class Meta:
        ordering = ['date', 'pk']
        verbose_name = "Director's Loan"
        verbose_name_plural = "Director's Loans"

    def __str__(self):
        return f"{self.date} {self.get_direction_display()} ${self.amount}"

    @classmethod
    def record_personal_expense(cls, transaction):
        """Mirror a personal expense paid off the company account into the loan.

        Direction is 'repayment' (Company → Director): the company has already
        paid money out on the director's behalf, so the balance it still owes
        them drops by that amount. Without this the excluded Transaction row is
        the only trace and current_balance() understates what is owed back.

        Idempotent — returns None if this transaction is already mirrored, so it
        is safe to call from both the CSV import and the admin action.
        """
        if cls.objects.filter(source_transaction=transaction).exists():
            return None
        return cls.objects.create(
            date=transaction.date,
            amount=transaction.gross_amount,
            direction='repayment',
            description=f"Personal expense on company account — "
                        f"{transaction.description}"[:255],
            source_transaction=transaction,
        )

    @classmethod
    def current_balance(cls):
        """Outstanding balance = contributions − repayments.

        Positive → company still owes the director.
        Zero     → settled.
        Negative → the director owes the company that much back. Personal spend
                   mirrored by record_personal_expense() lands here, so a
                   negative balance is a normal state, not just over-repayment.
        """
        agg = cls.objects.values('direction').annotate(total=Sum('amount'))
        totals = {row['direction']: row['total'] for row in agg}
        contributions = totals.get('contribution') or Decimal('0')
        repayments    = totals.get('repayment')    or Decimal('0')
        return contributions - repayments
