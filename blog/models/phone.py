from django.db import models


class PhoneMapping(models.Model):
    from_number = models.CharField(max_length=20, db_index=True)
    to_number = models.CharField(max_length=20)
    driver_name = models.CharField(max_length=100, blank=True, null=True)
    pickup_date = models.DateField(blank=True, null=True)
    pickup_time = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
