"""
Management command: fill distance_km for RegionSuburb records where it is null.

Strategy:
  - Google Maps Distance Matrix API (batched, 25 destinations/call)
    → used when settings.GOOGLE_MAPS_API_KEY is set
  - Nominatim (geocode) + OSRM (route)
    → free fallback, no key required, 1 req/sec rate limit

Usage:
    python manage.py fill_suburb_distances
    python manage.py fill_suburb_distances --region sydney
    python manage.py fill_suburb_distances --dry-run
"""
import time
from decimal import Decimal
from itertools import islice

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from regions.models import RegionSuburb

GMAPS_DIST_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
NOMINATIM_URL  = "https://nominatim.openstreetmap.org/search"
OSRM_URL       = "https://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=false"
HEADERS        = {"User-Agent": "EasyGoShuttle/1.0 (info@easygoshuttle.com.au)"}
BATCH_SIZE     = 25  # Google Maps Distance Matrix limit


def chunked(iterable, size):
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch:
            break
        yield batch


class Command(BaseCommand):
    help = "Fill distance_km (airport → suburb driving distance) for null RegionSuburb records"

    def add_arguments(self, parser):
        parser.add_argument("--region", metavar="SLUG",
                            help="Limit to one region slug (e.g. sydney)")
        parser.add_argument("--dry-run", action="store_true",
                            help="Show distances without saving")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        gmaps_key = getattr(settings, "GOOGLE_MAPS_API_KEY", "") or ""

        self.stdout.write(f"Mode: {'Google Maps (batched)' if gmaps_key else 'Nominatim + OSRM'}")

        qs = (
            RegionSuburb.objects
            .filter(distance_km__isnull=True, region__primary_airport__isnull=False)
            .select_related("region__primary_airport")
            .order_by("region__name", "name")
        )
        if options["region"]:
            qs = qs.filter(region__slug=options["region"])

        suburbs = list(qs)
        total = len(suburbs)
        if not total:
            self.stdout.write("Nothing to fill.")
            return
        self.stdout.write(f"Processing {total} suburbs…\n")

        updated = skipped = errors = 0

        if gmaps_key:
            # ── Batched Google Maps approach ──────────────────────────────────
            # Group suburbs by airport so each batch shares one origin
            from itertools import groupby
            suburbs.sort(key=lambda s: s.region.primary_airport.code)

            for airport_code, group in groupby(suburbs, key=lambda s: s.region.primary_airport.code):
                group = list(group)
                airport = group[0].region.primary_airport
                origin = f"{airport.lat},{airport.lng}"

                for batch in chunked(group, BATCH_SIZE):
                    dests = [
                        f"{s.name}, {s.region.name}, {s.region.state_code or ''}, Australia"
                        for s in batch
                    ]
                    try:
                        distances = self._gmaps_batch(origin, dests, gmaps_key)
                    except Exception as exc:
                        self.stdout.write(f"  ERROR batch ({airport_code}): {exc}")
                        errors += len(batch)
                        continue

                    for suburb, km in zip(batch, distances):
                        if km is None:
                            self.stdout.write(f"  SKIP  {suburb.region.name} / {suburb.name}: no route")
                            skipped += 1
                        else:
                            self.stdout.write(f"  OK    {suburb.region.name} / {suburb.name}: {km:.1f} km")
                            if not dry_run:
                                suburb.distance_km = Decimal(str(round(km, 2)))
                                suburb.save(update_fields=["distance_km"])
                            updated += 1

        else:
            # ── One-by-one Nominatim + OSRM fallback ─────────────────────────
            for i, suburb in enumerate(suburbs, start=1):
                airport = suburb.region.primary_airport
                o_lat, o_lng = float(airport.lat), float(airport.lng)
                dest = f"{suburb.name}, {suburb.region.name}, {suburb.region.state_code or ''}, Australia"
                prefix = f"[{i}/{total}] {suburb.region.name} / {suburb.name}"

                try:
                    d_lat, d_lng = self._nominatim_geocode(dest)
                    km = self._osrm_distance(o_lat, o_lng, d_lat, d_lng)
                except Exception as exc:
                    self.stdout.write(f"  ERROR {prefix}: {exc}")
                    errors += 1
                    time.sleep(1.1)
                    continue

                self.stdout.write(f"  OK    {prefix}: {km:.1f} km")
                if not dry_run:
                    suburb.distance_km = Decimal(str(round(km, 2)))
                    suburb.save(update_fields=["distance_km"])
                updated += 1
                time.sleep(1.1)  # Nominatim: ≤ 1 req/sec

        label = "(dry run)" if dry_run else "saved"
        self.stdout.write(
            f"\nDone ({label}): updated={updated}  skipped={skipped}  errors={errors}"
        )

    # ── Google Maps Distance Matrix (batched) ─────────────────────────────────

    def _gmaps_batch(self, origin: str, destinations: list, key: str) -> list:
        """Return a list of km values (or None) aligned with destinations."""
        resp = requests.get(
            GMAPS_DIST_URL,
            params={
                "origins": origin,
                "destinations": "|".join(destinations),
                "mode": "driving",
                "key": key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            raise ValueError(f"API status: {data.get('status')} — {data.get('error_message', '')}")

        results = []
        for element in data["rows"][0]["elements"]:
            if element.get("status") == "OK":
                results.append(element["distance"]["value"] / 1000)
            else:
                results.append(None)
        return results

    # ── Nominatim geocoding ───────────────────────────────────────────────────

    def _nominatim_geocode(self, query: str):
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "au"},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            raise ValueError(f"No geocode result for '{query}'")
        return float(results[0]["lat"]), float(results[0]["lon"])

    # ── OSRM driving distance ─────────────────────────────────────────────────

    def _osrm_distance(self, lat1, lng1, lat2, lng2) -> float:
        url = OSRM_URL.format(lng1=lng1, lat1=lat1, lng2=lng2, lat2=lat2)
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok":
            raise ValueError(f"OSRM: {data.get('message', data.get('code'))}")
        return data["routes"][0]["distance"] / 1000
