from django.db import models


class PhoneMapping(models.Model):
    # One mapping per booking, not per customer number — a repeat customer
    # with two concurrent bookings needs both drivers reachable at once, so a
    # second booking's mapping must not delete the first's.
    post = models.ForeignKey(
        'Post', on_delete=models.CASCADE, null=True, blank=True,
        related_name='phone_mappings',
    )
    from_number = models.CharField(max_length=20, db_index=True)
    to_number = models.CharField(max_length=20)
    driver_name = models.CharField(max_length=100, blank=True, null=True)
    pickup_date = models.DateField(blank=True, null=True)
    pickup_time = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
