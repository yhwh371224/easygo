from django.db import models


class Region(models.Model):
    # Core identity
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    state_code = models.CharField(max_length=10, blank=True)
    timezone = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_coming_soon = models.BooleanField(default=False)

    # Contact & location
    phone = models.CharField(max_length=20)
    phone_display = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # SEO
    meta_title = models.CharField(max_length=100, blank=True)
    meta_description = models.TextField(blank=True)

    # Guides & Terminals
    terminal_info = models.JSONField(blank=True, null=True)
    meeting_point = models.TextField(blank=True)
    arrival_guide = models.TextField(blank=True)
    # New scalable airport structure (backward compatible)
    airports = models.ManyToManyField("Airport", blank=True, related_name="regions")
    primary_airport = models.ForeignKey(
        "Airport",
        on_delete=models.PROTECT,
        related_name="primary_for_regions",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Airport(models.Model):
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="airports")
    city = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=150, blank=True)
    lat = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    lng = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.city}"


class Terminal(models.Model):
    class TerminalType(models.TextChoices):
        INTL = "intl", "International"
        DOMESTIC = "domestic", "Domestic"

    airport = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name="terminals")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TerminalType.choices)

    class Meta:
        ordering = ["airport__code", "type", "name"]
        unique_together = [("airport", "type", "name")]

    def __str__(self):
        return f"{self.airport.code} {self.get_type_display()} — {self.name}"


class RegionSuburb(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='suburbs')
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    zone = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    featured_order = models.PositiveSmallIntegerField(default=999)
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)

    # Dropdown ordering: pinned items (airports, terminals) appear first
    is_pinned = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('region', 'slug')
        ordering = ['featured_order', 'name']

    def __str__(self):
        return f"{self.region.name} — {self.name}"


class RequestLog(models.Model):
    region = models.ForeignKey("regions.Region", null=True, on_delete=models.SET_NULL)
    path = models.CharField(max_length=255)
    ip = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
