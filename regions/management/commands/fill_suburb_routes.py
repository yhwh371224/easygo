"""
Fill RegionSuburb.drive_minutes / drive_minutes_peak / route_summary.

- Drive times: Google Distance Matrix (the key has Distance Matrix but not
  Directions enabled), traffic prediction for the next Tuesday:
    off-peak 11:00 local, peak 07:30 local (morning rush towards the airport).
  Batched 25 suburbs per call.
- Main roads: OSRM public router (free, no key, ≤1 req/s) — the named roads that
  carry most of the distance, e.g. "M1 and Southern Cross Drive".

Usage:
    python manage.py fill_suburb_routes --region sydney --slugs hornsby,penrith --dry-run
    python manage.py fill_suburb_routes --region sydney --missing
"""
import datetime
import re
import time
from itertools import islice
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from regions.models import RegionSuburb

DM_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{o_lng},{o_lat};{d_lng},{d_lat}"
OFFPEAK = (11, 0)
PEAK = (7, 30)
BATCH = 25


def next_tuesday(tz_name, hour, minute):
    """Unix timestamp for the next Tuesday at least two days out, local time."""
    tz = ZoneInfo(tz_name or "Australia/Sydney")
    day = datetime.datetime.now(tz).date() + datetime.timedelta(days=2)
    while day.weekday() != 1:
        day += datetime.timedelta(days=1)
    return int(datetime.datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz).timestamp())


def origin_text(s):
    return f"{s.name} {s.region.state_code}, Australia"


_RAMP = re.compile(r"\b(on|off)[- ]?ramp\b|\bexit\b|\bslip\b", re.I)


def _road_name(step):
    """Readable road name: the street name ("Pacific Highway") over the route code
    ("A1"), minus ramp/exit pieces. Returns "" for steps not worth naming."""
    name = (step.get("name") or "").split(";")[0].strip()
    if not name:
        name = (step.get("ref") or "").split(";")[0].strip()
    ref = (step.get("ref") or "").split(";")[0].strip()
    if name and re.fullmatch(r"M\d+", ref) and ref not in name:
        name = f"{ref} {name}"  # "M4 Western Motorway" — how Sydneysiders say it
    if not name or _RAMP.search(name):
        return re.sub(r"\s*\b(Tunnel )?(On|Off)[- ]?ramp\b", "", name, flags=re.I).strip() if name and re.search(r"(On|Off)[- ]?ramp", name, re.I) else ""
    return name


def main_roads(steps, top=2):
    """Pick the named roads covering the most distance, in driving order."""
    dist = {}
    order = []
    for st in steps:
        name = _road_name(st)
        if not name:
            continue
        if name not in dist:
            order.append(name)
        dist[name] = dist.get(name, 0) + st.get("distance", 0)
    best = sorted(dist, key=dist.get, reverse=True)[:top]
    return " and ".join(n for n in order if n in best)


class Command(BaseCommand):
    help = "Fill drive time (off-peak / peak) and main roads from each suburb to its airport"

    def add_arguments(self, parser):
        parser.add_argument("--region", metavar="SLUG")
        parser.add_argument("--slugs", help="Comma-separated suburb slugs")
        parser.add_argument("--missing", action="store_true", help="Only suburbs without drive_minutes")
        parser.add_argument("--no-roads", action="store_true", help="Skip the OSRM main-road lookup")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        key = getattr(settings, "GOOGLE_MAPS_API_KEY", "") or ""
        if not key:
            raise CommandError("GOOGLE_MAPS_API_KEY is not set")

        qs = (
            RegionSuburb.objects
            .filter(is_active=True, region__primary_airport__isnull=False)
            .select_related("region__primary_airport")
            .order_by("region__slug", "name")
        )
        if opts["region"]:
            qs = qs.filter(region__slug=opts["region"])
        if opts["slugs"]:
            qs = qs.filter(slug__in=[s.strip() for s in opts["slugs"].split(",") if s.strip()])
        if opts["missing"]:
            qs = qs.filter(drive_minutes__isnull=True)
        suburbs = list(qs)
        self.stdout.write(f"{len(suburbs)} suburbs")

        ok = failed = 0
        by_region = {}
        for s in suburbs:
            by_region.setdefault(s.region_id, []).append(s)
        for group in by_region.values():
            region = group[0].region
            airport = region.primary_airport
            dest = f"{airport.lat},{airport.lng}"
            it = iter(group)
            while batch := list(islice(it, BATCH)):
                try:
                    off = self._matrix(batch, dest, next_tuesday(region.timezone, *OFFPEAK), key)
                    peak = self._matrix(batch, dest, next_tuesday(region.timezone, *PEAK), key)
                except Exception as exc:
                    failed += len(batch)
                    self.stdout.write(f"  FAIL batch {region.slug}: {exc}")
                    continue
                for s, off_min, peak_min in zip(batch, off, peak):
                    if off_min is None:
                        failed += 1
                        self.stdout.write(f"  FAIL  {region.slug}/{s.slug}: no route")
                        continue
                    roads = "" if opts["no_roads"] else self._roads(s, airport, key)
                    ok += 1
                    self.stdout.write(f"  OK    {region.slug}/{s.slug}: {off_min} min (peak {peak_min}) via {roads or '-'}")
                    if not opts["dry_run"]:
                        s.drive_minutes = off_min
                        s.drive_minutes_peak = peak_min
                        if roads:
                            s.route_summary = roads[:120]
                        s.route_checked_at = timezone.now()
                        s.save(update_fields=["drive_minutes", "drive_minutes_peak", "route_summary", "route_checked_at"])
        self.stdout.write(f"Done{' (dry run)' if opts['dry_run'] else ''}: ok={ok} failed={failed}")

    def _matrix(self, batch, dest, departure, key):
        resp = requests.get(DM_URL, params={
            "origins": "|".join(origin_text(s) for s in batch),
            "destinations": dest,
            "mode": "driving",
            "departure_time": departure,
            "traffic_model": "best_guess",
            "region": "au",
            "key": key,
        }, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            raise ValueError(f"{data.get('status')} {data.get('error_message', '')}".strip())
        out = []
        for row in data["rows"]:
            el = row["elements"][0]
            if el.get("status") != "OK":
                out.append(None)
                continue
            out.append(round((el.get("duration_in_traffic") or el["duration"])["value"] / 60))
        return out

    def _roads(self, s, airport, key):
        """Main roads via OSRM. Needs coordinates: the suburb's own, else Google geocode."""
        try:
            lat, lng = s.latitude, s.longitude
            if lat is None or lng is None:
                g = requests.get(GEOCODE_URL, params={"address": origin_text(s), "key": key}, timeout=15).json()
                if g.get("status") == "OK":
                    loc = g["results"][0]["geometry"]["location"]
                    lat, lng = loc["lat"], loc["lng"]
                else:
                    # 키에 Geocoding 이 안 켜져 있으면 무료 Nominatim (≤1 req/s)
                    time.sleep(1.1)
                    n = requests.get(NOMINATIM_URL, params={
                        "q": origin_text(s), "format": "json", "limit": 1, "countrycodes": "au",
                    }, headers={"User-Agent": "EasyGoShuttle/1.0"}, timeout=15).json()
                    if not n:
                        return ""
                    lat, lng = n[0]["lat"], n[0]["lon"]
            time.sleep(1.1)  # OSRM public server: ≤1 req/s
            r = requests.get(OSRM_URL.format(o_lng=lng, o_lat=lat, d_lng=airport.lng, d_lat=airport.lat),
                             params={"steps": "true", "overview": "false"}, timeout=15,
                             headers={"User-Agent": "EasyGoShuttle/1.0"})
            r.raise_for_status()
            steps = r.json()["routes"][0]["legs"][0]["steps"]
            return main_roads(steps)
        except Exception as exc:
            self.stdout.write(f"    roads lookup failed for {s.slug}: {exc}")
            return ""
