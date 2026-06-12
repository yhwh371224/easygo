from django.db import models


class PayrollEntry(models.Model):
    """Owner wage records for STP / superannuation tracking.

    Standalone model — not derived from any existing model.
    """

    pay_date = models.DateField()
    period_start = models.DateField()
    period_end = models.DateField()
    employee_name = models.CharField(max_length=120, default="Sung Kam")
    gross_pay = models.DecimalField(max_digits=10, decimal_places=2)
    paygw_withheld = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    super_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name_plural = "Payroll entries"

    def __str__(self):
        return f"{self.employee_name} {self.pay_date} {self.net_pay}"
