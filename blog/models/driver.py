from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class VirtualNumber(models.Model):
    number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.number


class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    must_change_password = models.BooleanField(default=True)
    region = models.ForeignKey('regions.Region', null=True, blank=True, on_delete=models.SET_NULL)
    is_default = models.BooleanField(default=False)
    driver_name = models.CharField(max_length=100, blank=True, null=True)
    driver_contact = models.CharField(max_length=50, blank=True, null=True)
    driver_email = models.EmailField(blank=True, null=True)
    driver_address = models.CharField(max_length=200, blank=True, null=True)
    driver_plate = models.CharField(max_length=30, blank=True, null=True)
    driver_car = models.CharField(max_length=30, blank=True, null=True)
    driver_bankdetails = models.TextField(blank=True, null=True)
    google_calendar_id = models.CharField(max_length=255, blank=True, null=True)
    virtual_number = models.ForeignKey('VirtualNumber', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.driver_name


class DriverSettlement(models.Model):
    driver = models.ForeignKey('Driver', on_delete=models.CASCADE, related_name='settlements')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True, null=True)
    settled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    settled_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-settled_at']

    @property
    def local_date(self):
        import pytz
        from django.utils.timezone import localtime
        try:
            tz = pytz.timezone(self.driver.region.timezone)
            return self.settled_at.astimezone(tz).date()
        except Exception:
            return localtime(self.settled_at).date()

    def __str__(self):
        return f"{self.driver} - ${self.amount} on {self.local_date}"
