from django.db import models


class Region(models.Model):
    # Core identity
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    state_code = models.CharField(max_length=10, blank=True)
    timezone = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    # Airport
    airport_code = models.CharField(max_length=10)
    airport_name = models.CharField(max_length=100, blank=True)
    airport_lat = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    airport_lng = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # Contact & location
    phone = models.CharField(max_length=20)
    phone_display = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # SEO
    meta_description = models.TextField(blank=True)

    # Guides & Terminals
    terminal_info = models.JSONField(blank=True, null=True)
    meeting_point = models.TextField(blank=True)
    arrival_guide = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class RegionSuburb(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='suburbs')
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    zone = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = ('region', 'slug')
        ordering = ['zone', 'name']

    def __str__(self):
        return f"{self.region.name} — {self.name}"
