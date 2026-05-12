"""
Sync airport pickup data for Sydney and Melbourne into the normalised structure:
  Airport → Terminal → TerminalPickupPoint → PickupPointMap

Idempotent: safe to run multiple times. Uses get_or_create throughout.

Usage:
    python manage.py sync_airport_pickup_data          # both airports
    python manage.py sync_airport_pickup_data --sydney
    python manage.py sync_airport_pickup_data --melbourne
"""

from django.core.management.base import BaseCommand, CommandError

from regions.models import Airport, Terminal, TerminalPickupPoint, PickupPointMap


# ──────────────────────────────────────────────────────────────────────────────
# Seed data
# ──────────────────────────────────────────────────────────────────────────────

SYDNEY = {
    "code": "SYD",
    "terminals": [
        {
            "name": "T1 International",
            "type": Terminal.TerminalType.INTL,
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "After clearing customs, exit through the arrivals hall and follow "
                        "signs to the Ground Transport pickup zone on Level 0 (roadway level). "
                        "Your EasyGo driver will be waiting with a name board at the "
                        "designated pickup bay."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.LOCATION,
                            "title": "T1 Ground Transport Pickup Zone",
                            "url": "https://www.sydneyairport.com.au/info-sheet/ground-transport-t1",
                        },
                        {
                            "type": PickupPointMap.MapType.GOOGLE,
                            "title": "T1 Arrivals — Google Maps",
                            "url": "https://maps.app.goo.gl/T1SydneyAirportArrivals",
                        },
                    ],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare and TNC pickups are located in the multi-storey car park "
                        "(P1) on the T1 precinct, Level 1. Exit the arrivals hall, follow the "
                        "pedestrian path to the car park, and take the lift to Level 1. "
                        "Follow 'Rideshare' signs to your bay."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.WALKING,
                            "title": "T1 Rideshare Pickup — Walking Route",
                            "url": "https://www.sydneyairport.com.au/info-sheet/rideshare-t1",
                        },
                    ],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside directly "
                        "outside the T1 arrivals exit, clearly marked with disability "
                        "parking bays. Please notify EasyGo at booking time if you require "
                        "an accessible vehicle so we can arrange the correct bay."
                    ),
                    "maps": [],
                },
                {
                    "name": "Shuttle Bus Pickup",
                    "instruction": (
                        "Shared shuttle buses depart from the T1 Ground Transport Centre on "
                        "Level 0 of the terminal. Follow 'Buses & Coaches' signs after "
                        "exiting customs. EasyGo shared shuttles use the coach bays — your "
                        "confirmation email will specify the bay number."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.LOCATION,
                            "title": "T1 Coach & Shuttle Bay Map",
                            "url": "https://www.sydneyairport.com.au/info-sheet/coaches-t1",
                        },
                    ],
                },
            ],
        },
        {
            "name": "T2 Domestic",
            "type": Terminal.TerminalType.DOMESTIC,
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Exit baggage claim and follow signs to the kerbside pickup zone "
                        "directly outside the T2 terminal. Your EasyGo driver will meet "
                        "you at the kerbside — check your confirmation email for the "
                        "exact bay number."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.LOCATION,
                            "title": "T2 Kerbside Pickup Zone",
                            "url": "https://www.sydneyairport.com.au/info-sheet/ground-transport-t2",
                        },
                    ],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups at T2 are on the kerbside roadway immediately "
                        "outside the arrivals exit. Follow the 'Rideshare' signage on the "
                        "footpath. Your driver will confirm the exact bay via the app."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside outside the "
                        "T2 arrivals exit, in the marked disability bays. Please notify "
                        "EasyGo in advance to arrange the correct vehicle."
                    ),
                    "maps": [],
                },
            ],
        },
        {
            "name": "T3 Qantas",
            "type": Terminal.TerminalType.DOMESTIC,
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Exit baggage claim at T3 and follow signs to the kerbside pickup "
                        "zone directly outside the terminal. Your EasyGo driver will meet "
                        "you at the kerbside — check your confirmation email for the exact "
                        "bay number."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.LOCATION,
                            "title": "T3 Kerbside Pickup Zone",
                            "url": "https://www.sydneyairport.com.au/info-sheet/ground-transport-t3",
                        },
                    ],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups at T3 are on the lower kerbside roadway. "
                        "Follow the 'Rideshare' signs immediately outside the arrivals exit. "
                        "Your driver will confirm the exact bay via the app."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside outside the "
                        "T3 arrivals exit. Please notify EasyGo in advance to arrange the "
                        "correct vehicle."
                    ),
                    "maps": [],
                },
            ],
        },
    ],
}


MELBOURNE = {
    "code": "MEL",
    "terminals": [
        {
            "name": "T1 International",
            "type": Terminal.TerminalType.INTL,
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Arrivals at Level 2 (Ground Level). After clearing customs, exit "
                        "through the sliding doors into the Arrivals Hall. Your EasyGo "
                        "driver will be waiting with a name board near the exit."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.LOCATION,
                            "title": "T1 Arrivals Hall — Pickup Zone",
                            "url": "https://www.melbourneairport.com.au/passengers/terminal-maps/t1",
                        },
                        {
                            "type": PickupPointMap.MapType.GOOGLE,
                            "title": "T1 International Arrivals — Google Maps",
                            "url": "https://maps.app.goo.gl/MELTerminal1Arrivals",
                        },
                    ],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups are located on Level 1 of the T1 car park. "
                        "Exit the arrivals hall, take the lift or stairs to Level 1, and "
                        "follow the 'Rideshare' signs to your bay."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.WALKING,
                            "title": "T1 Rideshare Pickup — Walking Route",
                            "url": "https://www.melbourneairport.com.au/passengers/getting-here/rideshare",
                        },
                    ],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside directly "
                        "outside the T1 arrivals exit, Level 2, in the marked disability "
                        "bays. Please notify EasyGo at booking time if you require an "
                        "accessible vehicle."
                    ),
                    "maps": [],
                },
                {
                    "name": "Shuttle Bus Pickup",
                    "instruction": (
                        "Shared shuttle services depart from the Ground Transport hub on "
                        "Level 1 of T1. Follow 'Buses & Coaches' signs after exiting "
                        "customs. EasyGo shared shuttles use the coach bays — your "
                        "confirmation email will specify the bay number."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.LOCATION,
                            "title": "T1 Ground Transport Hub Map",
                            "url": "https://www.melbourneairport.com.au/passengers/getting-here/coaches",
                        },
                    ],
                },
            ],
        },
        {
            "name": "T2 Qantas Domestic",
            "type": Terminal.TerminalType.DOMESTIC,
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Collect your baggage and exit through the main Arrivals door. "
                        "Your driver meets you on the kerbside directly outside baggage claim."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.LOCATION,
                            "title": "T2 Kerbside Pickup Zone",
                            "url": "https://www.melbourneairport.com.au/passengers/terminal-maps/t2",
                        },
                    ],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups at T2 are on the kerbside roadway immediately "
                        "outside the arrivals exit. Follow the 'Rideshare' signs on the "
                        "footpath."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside outside T2 "
                        "arrivals, in the marked disability bays. Please notify EasyGo in "
                        "advance to arrange the correct vehicle."
                    ),
                    "maps": [],
                },
            ],
        },
        {
            "name": "T3 Virgin / Rex Domestic",
            "type": Terminal.TerminalType.DOMESTIC,
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Connected to T2 via a short walkway. Exit at Ground Level. "
                        "Your driver meets you at the main kerbside exit."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.LOCATION,
                            "title": "T3 Kerbside Pickup Zone",
                            "url": "https://www.melbourneairport.com.au/passengers/terminal-maps/t3",
                        },
                    ],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups at T3 are on the kerbside roadway immediately "
                        "outside the arrivals exit. Follow the 'Rideshare' signs."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside outside T3 "
                        "arrivals. Please notify EasyGo in advance to arrange the correct "
                        "vehicle."
                    ),
                    "maps": [],
                },
            ],
        },
        {
            "name": "T4 Budget Airlines (Jetstar & others)",
            "type": Terminal.TerminalType.DOMESTIC,
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Separate terminal on Departure Drive. After collecting baggage, "
                        "exit through the main doors. Your driver meets you on the "
                        "pick-up kerbside."
                    ),
                    "maps": [
                        {
                            "type": PickupPointMap.MapType.LOCATION,
                            "title": "T4 Kerbside Pickup Zone",
                            "url": "https://www.melbourneairport.com.au/passengers/terminal-maps/t4",
                        },
                    ],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups at T4 are on the kerbside roadway immediately "
                        "outside the arrivals exit. Follow the 'Rideshare' signs."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside outside T4 "
                        "arrivals. Please notify EasyGo in advance to arrange the correct "
                        "vehicle."
                    ),
                    "maps": [],
                },
            ],
        },
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# Command
# ──────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        "Sync Sydney and Melbourne airport pickup data into the normalised "
        "Airport → Terminal → TerminalPickupPoint → PickupPointMap structure. "
        "Idempotent — safe to run multiple times."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--sydney",
            action="store_true",
            help="Sync Sydney Airport only.",
        )
        parser.add_argument(
            "--melbourne",
            action="store_true",
            help="Sync Melbourne Airport only.",
        )

    def handle(self, *args, **options):
        run_sydney = options["sydney"]
        run_melbourne = options["melbourne"]
        run_all = not run_sydney and not run_melbourne

        if run_all or run_sydney:
            self.sync_sydney()
        if run_all or run_melbourne:
            self.sync_melbourne()

        self.stdout.write(self.style.SUCCESS("\nAll done."))

    # ── public sync methods ──────────────────────────────────────────────────

    def sync_sydney(self):
        self.stdout.write("\nSyncing Sydney Airport (SYD)…")
        self._sync_airport(SYDNEY)
        self.stdout.write(self.style.SUCCESS("Sydney sync complete."))

    def sync_melbourne(self):
        self.stdout.write("\nSyncing Melbourne Airport (MEL)…")
        self._sync_airport(MELBOURNE)
        self.stdout.write(self.style.SUCCESS("Melbourne sync complete."))

    # ── internals ───────────────────────────────────────────────────────────

    def _sync_airport(self, data: dict):
        code = data["code"]
        try:
            airport = Airport.objects.get(code=code)
        except Airport.DoesNotExist:
            raise CommandError(f"Airport with code '{code}' not found in the database.")

        for t_data in data["terminals"]:
            terminal = self._sync_terminal(airport, t_data)
            for pp_data in t_data["pickup_points"]:
                pickup_point = self._sync_pickup_point(terminal, pp_data)
                for map_data in pp_data["maps"]:
                    self._sync_map(pickup_point, map_data)

    def _sync_terminal(self, airport: Airport, data: dict) -> Terminal:
        terminal, created = Terminal.objects.get_or_create(
            airport=airport,
            type=data["type"],
            name=data["name"],
        )
        status = "created" if created else "exists"
        self.stdout.write(f"  [{status}] Terminal: {terminal}")
        return terminal

    def _sync_pickup_point(self, terminal: Terminal, data: dict) -> TerminalPickupPoint:
        pp, created = TerminalPickupPoint.objects.get_or_create(
            terminal=terminal,
            name=data["name"],
            defaults={"instruction": data["instruction"]},
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"    [created] Pickup point: {pp.name}"))
        else:
            # Refresh instruction if the DB copy is blank and we have content.
            if not pp.instruction and data["instruction"]:
                pp.instruction = data["instruction"]
                pp.save(update_fields=["instruction"])
                self.stdout.write(f"    [updated] Pickup point: {pp.name} (instruction set)")
            else:
                self.stdout.write(f"    [exists]  Pickup point: {pp.name}")

        return pp

    def _sync_map(self, pickup_point: TerminalPickupPoint, data: dict) -> PickupPointMap:
        m, created = PickupPointMap.objects.get_or_create(
            pickup_point=pickup_point,
            url=data["url"],
            defaults={
                "type": data["type"],
                "title": data["title"],
            },
        )
        status = "created" if created else "exists"
        self.stdout.write(f"      [{status}] Map ({m.get_type_display()}): {m.title}")
        return m
