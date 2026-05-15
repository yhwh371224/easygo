from django.db import models


class RegionSuburb(models.Model):
    region = models.ForeignKey("Region", on_delete=models.CASCADE, related_name="suburbs")
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    zone = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    featured_order = models.PositiveSmallIntegerField(default=999)
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    carousel_image = models.CharField(
        max_length=255,
        blank=True,
        help_text="Carousel card image URL, e.g. /static/regions/photos/chatswood.webp",
    )

    distance_km = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Drive distance from airport in km (used for distance-based pricing)",
    )

    # Pinned items (airports, terminals) appear first in dropdowns
    is_pinned = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("region", "slug")
        ordering = ["featured_order", "name"]

    def __str__(self):
        return f"{self.region.name} — {self.name}"
