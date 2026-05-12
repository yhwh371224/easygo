from django.db import models


class Airport(models.Model):
    country = models.ForeignKey("Country", on_delete=models.PROTECT, related_name="airports")
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


class TerminalPickupPoint(models.Model):
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.CASCADE,
        related_name="pickup_points",
    )
    name = models.CharField(max_length=100)
    instruction = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.terminal} — {self.name}"


class PickupPointMap(models.Model):
    class MapType(models.TextChoices):
        LOCATION = "location", "Location Map"
        WALKING = "walking", "Walking Route"
        GOOGLE = "google", "Google Map"
        PDF = "pdf", "PDF Guide"
        IMAGE = "image", "Image Map"

    pickup_point = models.ForeignKey(
        "TerminalPickupPoint",
        on_delete=models.CASCADE,
        related_name="maps",
    )

    type = models.CharField(
        max_length=20,
        choices=MapType.choices,
        default=MapType.LOCATION,
    )

    title = models.CharField(max_length=255)
    url = models.URLField()

    class Meta:
        ordering = ["pickup_point", "type", "title"]

    def __str__(self):
        return f"{self.pickup_point} — {self.get_type_display()} — {self.title}"
