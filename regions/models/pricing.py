from django.db import models


class VehicleType(models.Model):
    slug             = models.SlugField(unique=True)  # "sedan", "van", "bus"
    name             = models.CharField(max_length=50)
    capacity_pax     = models.PositiveSmallIntegerField()
    price_multiplier = models.DecimalField(max_digits=4, decimal_places=2)
    is_active        = models.BooleanField(default=True)

    class Meta:
        ordering = ["capacity_pax"]

    def __str__(self):
        return f"{self.name} (×{self.price_multiplier})"


class SpecialItemType(models.Model):
    slug      = models.SlugField(unique=True)  # "ski", "snowboard", "golf"
    name      = models.CharField(max_length=50)
    fee       = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (${self.fee})"


class PricingRule(models.Model):
    region = models.OneToOneField(
        "Region", on_delete=models.CASCADE, related_name="pricing_rule"
    )

    rate_per_km             = models.DecimalField(max_digits=5, decimal_places=2, default=2.50)
    extra_bag_fee           = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    oversize_fee            = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    second_stop_fee         = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    pax_surcharge_mid_fee     = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    pax_surcharge_large_fee   = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    special_item_fee          = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    special_item_oversize_fee = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)

    peak_windows = models.JSONField(
        default=list,
        help_text=(
            'List of time windows with surcharges. Example: '
            '[{"type":"peak","start":6,"end":9,"surcharge_rate":0.20}]'
        ),
    )

    class Meta:
        verbose_name = "Pricing Rule"

    def __str__(self):
        return f"PricingRule — {self.region}"
