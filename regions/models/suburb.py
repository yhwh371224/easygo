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

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text="WGS84 latitude of the suburb/terminal centroid",
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text="WGS84 longitude of the suburb/terminal centroid",
    )

    # 공항까지 실제 운전 시간·경로 (Google Directions, `manage.py fill_suburb_routes`).
    # 수버브 페이지마다 다른 실제 정보를 보여주기 위한 값 — 비어 있으면 페이지에서 뺀다.
    drive_minutes = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Typical off-peak drive to the airport (weekday late morning), minutes",
    )
    drive_minutes_peak = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Weekday morning-peak drive to the airport, minutes",
    )
    route_summary = models.CharField(
        max_length=120, blank=True, help_text='Main roads Google picks, e.g. "M2 and Lane Cove Tunnel"',
    )
    route_checked_at = models.DateTimeField(null=True, blank=True)
    local_content = models.TextField(
        blank=True,
        help_text="Hand-written HTML for this suburb (top suburbs only). When set it replaces the "
                  "generic intro / 'Ideal for' / 'Booking in advance' blocks on the suburb page.",
    )

    # Pinned items (airports, terminals) appear first in dropdowns
    is_pinned = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("region", "slug")
        ordering = ["featured_order", "name"]

    def __str__(self):
        return f"{self.region.name} — {self.name}"

    @property
    def from_price(self):
        """페이지에 보여주는 "From $" — 실제 견적과 같은 가격 규칙으로 계산한
        가장 싼 견적(1–2명, 할증 없는 시간). price 필드는 규칙이 없을 때만 쓴다."""
        if not hasattr(self, "_from_price"):
            from regions.pricing import suburb_from_price
            self._from_price = suburb_from_price(self)
        return self._from_price

    @property
    def zone_phrase(self):
        """"Sydney's Outer West" — 구역 이름에 이미 도시 이름이 있으면 그대로."""
        label = self.zone_label
        city = self.region.name if self.region_id else ""
        if not label or (city and city.lower() in label.lower()):
            return label or city
        return f"{city}'s {label}" if city else label

    # 화면용 구역 이름. Sydney 는 zone 이 "outer_west" 같은 내부 코드라서 그대로 찍으면
    # 페이지에 "Penrith is located in outer_west" 처럼 나간다.
    _ZONE_WORDS = {"cbd": "CBD"}

    @property
    def zone_label(self):
        zone = (self.zone or "").strip()
        if not zone or (zone != zone.lower() and "_" not in zone):
            return zone  # 이미 사람이 읽는 이름 (Melbourne / Gold Coast 등)
        words = zone.replace("_", " ").split()
        return " ".join(self._ZONE_WORDS.get(w.lower(), w.capitalize()) for w in words)
