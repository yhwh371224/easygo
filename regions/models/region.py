from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


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

    # Hero background image filename (e.g. "melbourneairport.webp").
    # Falls back to "{slug}airport.webp" when blank.
    hero_image = models.CharField(max_length=200, blank=True)

    # Service areas displayed on the region home page
    service_areas = models.JSONField(blank=True, null=True)

    # Kept for backward compatibility — remove after template migration
    terminal_info = models.JSONField(blank=True, null=True)
    meeting_point = models.TextField(blank=True)
    arrival_guide = models.TextField(blank=True)

    # Scalable airport structure
    airports = models.ManyToManyField("Airport", blank=True, related_name="regions")
    primary_airport = models.ForeignKey(
        "Airport",
        on_delete=models.PROTECT,
        related_name="primary_for_regions",
        null=True,
        blank=True,
    )

    @property
    def hero_image_file(self):
        return self.hero_image or f"{self.slug}airport.webp"

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
