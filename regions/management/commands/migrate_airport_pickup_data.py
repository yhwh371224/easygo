"""
One-time data migration: normalise SYD and MEL airport pickup information
from Region.{meeting_point,arrival_guide,terminal_info} into the relational
Airport → Terminal → TerminalPickupPoint → PickupPointMap structure.

Safe to run multiple times (idempotent via get_or_create + update_fields).
Old Region fields are NOT touched; template migration is a separate step.
"""

from django.core.management.base import BaseCommand
from regions.models import Airport, Terminal, TerminalPickupPoint, PickupPointMap


# ---------------------------------------------------------------------------
# Source data
# ---------------------------------------------------------------------------

SYDNEY_DATA = {
    "code": "SYD",
    "terminals": [
        {
            "old_name": "Sydney Intl Airport",
            "new_name": "T1 International",
            "type": "intl",
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "After clearing customs, exit through the arrivals hall and follow "
                        "signs to the Ground Transport pickup zone on Level 0 (roadway level). "
                        "Your EasyGo driver will be waiting with a name board at the designated "
                        "pickup bay."
                    ),
                    "maps": [],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare and TNC pickups are located in the multi-storey car park "
                        "(P1) on the T1 precinct, Level 1. Follow the 'Rideshare' signs after "
                        "exiting the arrivals hall."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside directly "
                        "outside the T1 arrivals exit. Please notify EasyGo in advance if you "
                        "require an accessible vehicle."
                    ),
                    "maps": [],
                },
                {
                    "name": "Shuttle Bus Pickup",
                    "instruction": (
                        "Shared shuttle buses depart from the T1 Ground Transport Centre, "
                        "located on Level 0 of the terminal. Follow 'Buses & Coaches' signs "
                        "after exiting customs."
                    ),
                    "maps": [],
                },
            ],
        },
        {
            "old_name": "Sydney Domestic Airport",
            "new_name": "T2 Domestic",
            "type": "domestic",
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Exit baggage claim and follow signs to the kerbside pickup zone "
                        "directly outside the terminal. Your EasyGo driver will meet you "
                        "at the kerbside."
                    ),
                    "maps": [],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups at T2 are on the kerbside roadway. Follow "
                        "the 'Rideshare' signs immediately outside the arrivals exit."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside outside "
                        "the T2 arrivals exit. Please notify EasyGo in advance."
                    ),
                    "maps": [],
                },
            ],
        },
        {
            "old_name": None,
            "new_name": "T3 Qantas",
            "type": "domestic",
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Exit baggage claim and follow signs to the kerbside pickup zone "
                        "directly outside the T3 terminal. Your EasyGo driver will meet you "
                        "at the kerbside."
                    ),
                    "maps": [],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups at T3 are located on the lower kerbside roadway. "
                        "Follow the 'Rideshare' signs immediately outside the arrivals exit."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside outside "
                        "the T3 arrivals exit. Please notify EasyGo in advance."
                    ),
                    "maps": [],
                },
            ],
        },
    ],
}

# Melbourne terminal_info source text (verbatim from Region.terminal_info JSON)
MELBOURNE_DATA = {
    "code": "MEL",
    "terminals": [
        {
            "old_name": "Melbourne Int'l Airport",
            "new_name": "T1 International",
            "type": "intl",
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Arrivals at Level 2 (Ground Level). After clearing customs, exit "
                        "through the sliding doors into the Arrivals Hall. Your EasyGo driver "
                        "will be waiting with a name board near the exit."
                    ),
                    "maps": [],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups are located on Level 1 of the T1 car park. "
                        "Exit the arrivals hall, take the lift or stairs to Level 1, and "
                        "follow the 'Rideshare' signs."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside directly "
                        "outside the T1 arrivals exit, Level 2. Please notify EasyGo in "
                        "advance if you require an accessible vehicle."
                    ),
                    "maps": [],
                },
                {
                    "name": "Shuttle Bus Pickup",
                    "instruction": (
                        "Shared shuttle services depart from the Ground Transport hub on "
                        "Level 1 of T1. Follow 'Buses & Coaches' signs after exiting customs."
                    ),
                    "maps": [],
                },
            ],
        },
        {
            "old_name": "Melbourne Domestic Airport",
            "new_name": "T2 Qantas Domestic",
            "type": "domestic",
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Collect your baggage and exit through the main Arrivals door. "
                        "Your driver meets you on the kerbside directly outside baggage claim."
                    ),
                    "maps": [],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups at T2 are on the kerbside roadway immediately "
                        "outside the arrivals exit. Follow the 'Rideshare' signs."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside outside "
                        "T2 arrivals. Please notify EasyGo in advance."
                    ),
                    "maps": [],
                },
            ],
        },
        {
            "old_name": None,
            "new_name": "T3 Virgin / Rex Domestic",
            "type": "domestic",
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Connected to T2 via a short walkway. Exit at Ground Level. "
                        "Your driver meets you at the main kerbside exit."
                    ),
                    "maps": [],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups at T3 are on the kerbside roadway immediately "
                        "outside the arrivals exit."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside outside "
                        "T3 arrivals. Please notify EasyGo in advance."
                    ),
                    "maps": [],
                },
            ],
        },
        {
            "old_name": None,
            "new_name": "T4 Budget Airlines (Jetstar & others)",
            "type": "domestic",
            "pickup_points": [
                {
                    "name": "Public Pickup",
                    "instruction": (
                        "Separate terminal on Departure Drive. After collecting baggage, "
                        "exit through the main doors. Driver meets you on the pick-up kerbside."
                    ),
                    "maps": [],
                },
                {
                    "name": "Rideshare Pickup",
                    "instruction": (
                        "Rideshare pickups at T4 are on the kerbside roadway immediately "
                        "outside the arrivals exit."
                    ),
                    "maps": [],
                },
                {
                    "name": "Accessible Pickup",
                    "instruction": (
                        "Accessible vehicle pickup is available on the kerbside outside "
                        "T4 arrivals. Please notify EasyGo in advance."
                    ),
                    "maps": [],
                },
            ],
        },
    ],
}


class Command(BaseCommand):
    help = "Migrate SYD and MEL airport pickup data into the normalised structure."

    def handle(self, *args, **options):
        for airport_data in [SYDNEY_DATA, MELBOURNE_DATA]:
            self._migrate_airport(airport_data)
        self.stdout.write(self.style.SUCCESS("Airport pickup data migration complete."))

    def _migrate_airport(self, airport_data):
        code = airport_data["code"]
        try:
            airport = Airport.objects.get(code=code)
        except Airport.DoesNotExist:
            self.stderr.write(f"Airport {code} not found — skipping.")
            return

        self.stdout.write(f"\n=== {airport} ===")

        for t_data in airport_data["terminals"]:
            terminal = self._get_or_create_terminal(airport, t_data)
            for pp_data in t_data["pickup_points"]:
                pickup_point = self._get_or_create_pickup_point(terminal, pp_data)
                for map_data in pp_data["maps"]:
                    self._get_or_create_map(pickup_point, map_data)

    def _get_or_create_terminal(self, airport, t_data):
        new_name = t_data["new_name"]
        terminal_type = t_data["type"]
        old_name = t_data.get("old_name")

        # If a terminal with the target name already exists, use it.
        existing = Terminal.objects.filter(
            airport=airport, type=terminal_type, name=new_name
        ).first()
        if existing:
            self.stdout.write(f"  Terminal already exists: {existing}")
            return existing

        # If we have an old_name, rename the record instead of creating a new one.
        if old_name:
            try:
                terminal = Terminal.objects.get(
                    airport=airport, type=terminal_type, name=old_name
                )
                terminal.name = new_name
                terminal.save(update_fields=["name"])
                self.stdout.write(
                    self.style.WARNING(f"  Renamed terminal: '{old_name}' → '{new_name}'")
                )
                return terminal
            except Terminal.DoesNotExist:
                pass  # fall through to create

        terminal = Terminal.objects.create(
            airport=airport, type=terminal_type, name=new_name
        )
        self.stdout.write(self.style.SUCCESS(f"  Created terminal: {terminal}"))
        return terminal

    def _get_or_create_pickup_point(self, terminal, pp_data):
        name = pp_data["name"]
        instruction = pp_data["instruction"]

        pp, created = TerminalPickupPoint.objects.get_or_create(
            terminal=terminal,
            name=name,
            defaults={"instruction": instruction},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"    Created pickup point: {name}"))
        else:
            # Update instruction only if the DB copy is blank.
            if not pp.instruction and instruction:
                pp.instruction = instruction
                pp.save(update_fields=["instruction"])
                self.stdout.write(f"    Updated instruction for pickup point: {name}")
            else:
                self.stdout.write(f"    Pickup point already exists: {name}")
        return pp

    def _get_or_create_map(self, pickup_point, map_data):
        m, created = PickupPointMap.objects.get_or_create(
            pickup_point=pickup_point,
            url=map_data["url"],
            defaults={"title": map_data["title"]},
        )
        label = "Created" if created else "Exists"
        self.stdout.write(f"      {label} map: {m.title}")
        return m
