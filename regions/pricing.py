"""
Pricing calculation engine for EasyGo airport transfers.

Usage:
    rule   = get_pricing_rule(region_id)
    config = get_pricing_config(suburb, vehicle, rule)
    result = calculate_price(config, booking)
    data   = price_to_dict(result)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from django.core.cache import cache


# ── Config dataclasses ────────────────────────────────────────────────────────

@dataclass
class WindowConfig:
    """A single peak or night surcharge window."""
    window_type: str      # "peak" | "night"
    start: int            # start hour, inclusive (0-23)
    end: int              # end hour, inclusive (0-23)
    surcharge_rate: Decimal

    @classmethod
    def from_dict(cls, d: dict) -> "WindowConfig":
        return cls(
            window_type=d["type"],
            start=int(d["start"]),
            end=int(d["end"]),
            surcharge_rate=Decimal(str(d["surcharge_rate"])),
        )

    def matches_hour(self, hour: int) -> bool:
        return self.start <= hour <= self.end


@dataclass
class PricingConfig:
    base_fare: Decimal
    distance_km_base: Decimal
    rate_per_km: Decimal
    extra_bag_fee: Decimal
    oversize_fee: Decimal
    second_stop_fee: Decimal
    vehicle_multiplier: Decimal
    vehicle_capacity: int
    pax_surcharge_mid_fee: Decimal
    pax_surcharge_large_fee: Decimal
    windows: List[WindowConfig] = field(default_factory=list)


@dataclass
class ExtraItems:
    extra_bags: int = 0
    oversize_items: int = 0
    special_items: int = 0                           # legacy: uniform-fee count path
    special_item_fee: Decimal = Decimal("10.00")     # legacy: from SpecialItemType.fee
    special_items_fee_total: Decimal = Decimal("0.00")  # per-item JSON fee total
    extra_stop: int = 0                              # number of extra stops


@dataclass
class BookingInput:
    passengers: int
    pickup_hour: int                            # local time, 0-23
    extras: ExtraItems = field(default_factory=ExtraItems)
    has_second_stop: bool = False
    extra_distance_km: Decimal = Decimal("0.00")


# ── Core calculation ──────────────────────────────────────────────────────────

def calculate_price(config: PricingConfig, booking: BookingInput) -> dict:
    """
    Returns a breakdown dict with Decimal values:
        base, distance_charge, vehicle_subtotal,
        peak_surcharge, pax_surcharge, extra_fees, total
    """
    ZERO = Decimal("0.00")

    # 1. Distance charge
    total_km = config.distance_km_base + booking.extra_distance_km
    distance_charge = (total_km * config.rate_per_km).quantize(Decimal("0.01"))

    # 2. Vehicle subtotal (base fare + distance, scaled by vehicle multiplier)
    vehicle_subtotal = (
        (config.base_fare + distance_charge) * config.vehicle_multiplier
    ).quantize(Decimal("0.01"))

    # 3. Peak / night surcharge (first matching window wins)
    peak_surcharge = ZERO
    for window in config.windows:
        if window.matches_hour(booking.pickup_hour):
            peak_surcharge = (vehicle_subtotal * window.surcharge_rate).quantize(Decimal("0.01"))
            break

    # 4. Passenger surcharge
    pax = booking.passengers
    if pax >= 10:
        pax_surcharge = config.pax_surcharge_mid_fee + config.pax_surcharge_large_fee
    elif pax >= 5:
        pax_surcharge = config.pax_surcharge_mid_fee
    else:
        pax_surcharge = ZERO

    # 5. Extras
    ex = booking.extras
    extra_fees = (
        Decimal(ex.extra_bags)    * config.extra_bag_fee
        + Decimal(ex.oversize_items)  * config.oversize_fee
        + Decimal(ex.special_items)   * ex.special_item_fee      # legacy uniform-fee path
        + ex.special_items_fee_total                              # per-item JSON path
        + Decimal(ex.extra_stop)  * config.second_stop_fee       # multi-stop
        + (config.second_stop_fee if booking.has_second_stop else ZERO)  # legacy boolean
    ).quantize(Decimal("0.01"))

    total = (vehicle_subtotal + peak_surcharge + pax_surcharge + extra_fees).quantize(Decimal("0.01"))

    return {
        "base":             config.base_fare,
        "distance_charge":  distance_charge,
        "vehicle_subtotal": vehicle_subtotal,
        "peak_surcharge":   peak_surcharge,
        "pax_surcharge":    pax_surcharge,
        "extra_fees":       extra_fees,
        "total":            total,
    }


def price_to_dict(result: dict) -> dict:
    """Serialize a calculate_price result to JSON-safe strings."""
    return {k: str(v) for k, v in result.items()}


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_pricing_config(suburb, vehicle, rule) -> PricingConfig:
    """Assemble a PricingConfig from ORM objects."""
    return PricingConfig(
        base_fare               = suburb.price,
        distance_km_base        = suburb.distance_km or Decimal("0.00"),
        rate_per_km             = rule.rate_per_km,
        extra_bag_fee           = rule.extra_bag_fee,
        oversize_fee            = rule.oversize_fee,
        second_stop_fee         = rule.second_stop_fee,
        vehicle_multiplier      = vehicle.price_multiplier,
        vehicle_capacity        = vehicle.capacity_pax,
        pax_surcharge_mid_fee   = rule.pax_surcharge_mid_fee,
        pax_surcharge_large_fee = rule.pax_surcharge_large_fee,
        windows                 = [WindowConfig.from_dict(w) for w in rule.peak_windows],
    )


def get_pricing_rule(region_id: int):
    """Fetch PricingRule for a region, cached for 1 hour."""
    from regions.models import PricingRule  # local import avoids circular deps

    key = f"pricing_rule_{region_id}"
    rule = cache.get(key)
    if not rule:
        rule = PricingRule.objects.get(region_id=region_id)
        cache.set(key, rule, timeout=60 * 60)
    return rule


# ── Inquiry → BookingInput helper ─────────────────────────────────────────────

_NO_FEE_KEYS = frozenset({"baby", "booster", "pram"})
_OVERSIZE_SUFFIX = "_oversize"


def inquiry_to_pricing(inquiry, rule) -> "BookingInput":
    """
    Build a BookingInput from an Inquiry instance and a PricingRule.

    special_items JSON schema:
        {
            "ski": 2, "ski_oversize": true,
            "baby": 1,          # no fee — vehicle allocation only
            ...
        }
    Oversize flag keys (ending in _oversize) are boolean and are read
    alongside their base key; they are never iterated as quantity items.
    """
    items: dict = inquiry.special_items or {}
    fee_total = Decimal("0.00")

    for key, qty in items.items():
        if key.endswith(_OVERSIZE_SUFFIX):
            continue                   # handled via base key lookup below
        if key in _NO_FEE_KEYS:
            continue                   # baby / booster / pram — no charge
        qty = int(qty or 0)
        if not qty:
            continue
        is_oversize = bool(items.get(f"{key}{_OVERSIZE_SUFFIX}", False))
        fee = rule.special_item_oversize_fee if is_oversize else rule.special_item_fee
        fee_total += Decimal(qty) * fee

    extras = ExtraItems(
        special_items_fee_total=fee_total,
        extra_stop=int(inquiry.extra_stop or 0),
    )

    try:
        hour = int(str(inquiry.pickup_time).split(":")[0]) if inquiry.pickup_time else 0
    except (ValueError, IndexError):
        hour = 0

    return BookingInput(
        passengers=int(inquiry.no_of_passenger or 0),
        pickup_hour=hour,
        extras=extras,
        extra_distance_km=Decimal("0.00"),
    )
