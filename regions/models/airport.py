from django.db import models

from regions.models.region import Region


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
    icon = models.CharField(max_length=10, blank=True, default="✈️", help_text="Emoji shown on the tab button")
    note = models.TextField(blank=True, help_text="Shown as a tip inside the terminal panel (e.g. 'On landing simply turn on your mobile phone')")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["airport__code", "sort_order", "name"]
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
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_default_point = models.BooleanField(default=False, help_text="드라이버 하루 첫 번째 미지정 픽업에 자동 배정 (Public 등)")
    is_default_second = models.BooleanField(default=False, help_text="드라이버 하루 두 번째 이상 미지정 픽업에 자동 배정 (Rideshare 등)")

    class Meta:
        ordering = ["sort_order", "name"]

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
    

class CruiseTerminal(models.Model):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="cruise_terminals")
    name = models.CharField(max_length=150)
    lat = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=11, decimal_places=6, null=True, blank=True)
    distance_km = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, help_text="Distance from terminal to airport (km)")
    base_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Base price = distance_km × $3")

    def __str__(self):
        return self.name
