"""
Pricing calculation engine for EasyGo airport transfers.

Usage:
    rule    = get_pricing_rule(region_id)
    config  = build_config_from_rule(suburb_obj, rule)
    booking = inquiry_to_pricing(inquiry, rule)
    result  = calculate_price(config, booking)
    total   = result["total"]          # Decimal
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
    extra_bag_fee: Decimal
    oversize_fee: Decimal
    second_stop_fee: Decimal
    pax_surcharge_mid_fee: Decimal    # per-person rate from 2nd passenger ($10)
    pax_surcharge_large_fee: Decimal  # extra flat fee for 10+ passengers ($30)
    windows: List[WindowConfig] = field(default_factory=list)


@dataclass
class ExtraItems:
    extra_bags: int = 0
    oversize_items: int = 0
    special_items_fee_total: Decimal = Decimal("0.00")  # sum from special_items JSON
    extra_stop: int = 0


@dataclass
class BookingInput:
    passengers: int
    pickup_hour: int                            # local time, 0-23
    extras: ExtraItems = field(default_factory=ExtraItems)
    extra_distance_km: Decimal = Decimal("0.00")  # kept for API compat, unused


# ── Core calculation ──────────────────────────────────────────────────────────

def calculate_price(config: PricingConfig, booking: BookingInput) -> dict:
    """
    New pricing formula:

        total = base_fare
              + peak_surcharge          (base_fare × rate if pickup in window)
              + pax_surcharge           ((pax-1) × $10; +$30 extra for 10+)
              + extra_fees              (bags, oversize, special items, extra stops)

    Returns a breakdown dict with Decimal values.
    """
    ZERO = Decimal("0.00")

    # 1. Peak / night surcharge on base fare (first matching window wins)
    peak_surcharge = ZERO
    for window in config.windows:
        if window.matches_hour(booking.pickup_hour):
            peak_surcharge = (config.base_fare * window.surcharge_rate).quantize(Decimal("0.01"))
            break

    # 2. Passenger surcharge: +$10 per person from 2nd passenger, +$30 extra for 10+
    pax = booking.passengers
    if pax >= 2:
        pax_surcharge = Decimal(pax - 1) * config.pax_surcharge_mid_fee
        if pax >= 10:
            pax_surcharge += config.pax_surcharge_large_fee
    else:
        pax_surcharge = ZERO

    # 3. Extras
    ex = booking.extras
    extra_fees = (
        Decimal(ex.extra_bags)    * config.extra_bag_fee
        + Decimal(ex.oversize_items) * config.oversize_fee
        + ex.special_items_fee_total
        + Decimal(ex.extra_stop)  * config.second_stop_fee
    ).quantize(Decimal("0.01"))

    total = (config.base_fare + peak_surcharge + pax_surcharge + extra_fees).quantize(Decimal("0.01"))

    return {
        "base":           config.base_fare,
        "peak_surcharge": peak_surcharge,
        "pax_surcharge":  pax_surcharge,
        "extra_fees":     extra_fees,
        "total":          total,
    }


def price_to_dict(result: dict) -> dict:
    """Serialize a calculate_price result to JSON-safe strings."""
    return {k: str(v) for k, v in result.items()}


# ── DB helpers ────────────────────────────────────────────────────────────────

def build_config_from_rule(suburb, rule) -> PricingConfig:
    """Assemble a PricingConfig from a RegionSuburb and PricingRule."""
    return PricingConfig(
        base_fare=suburb.price,
        extra_bag_fee=rule.extra_bag_fee,
        oversize_fee=rule.oversize_fee,
        second_stop_fee=rule.second_stop_fee,
        pax_surcharge_mid_fee=rule.pax_surcharge_mid_fee,
        pax_surcharge_large_fee=rule.pax_surcharge_large_fee,
        windows=[WindowConfig.from_dict(w) for w in rule.peak_windows],
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


def inquiry_to_pricing(inquiry, rule) -> BookingInput:
    """
    Build a BookingInput from an Inquiry instance and a PricingRule.

    special_items JSON schema:
        {
            "ski": 2, "ski_oversize": true,
            "baby": 1,          # no fee
            ...
        }
    """
    items: dict = inquiry.special_items or {}
    fee_total = Decimal("0.00")

    for key, qty in items.items():
        if key.endswith(_OVERSIZE_SUFFIX):
            continue
        if key in _NO_FEE_KEYS:
            continue
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
    )


# ── Top-level inquiry price helper ────────────────────────────────────────────

def calculate_inquiry_price(inquiry, region) -> str | None:
    """
    Calculate and return the price total for an Inquiry before saving.
    Returns a string like "120.00", or None if suburb/rule lookup fails.
    """
    from regions.models import RegionSuburb

    if not region:
        return None

    try:
        rule = get_pricing_rule(region.id)
    except Exception:
        return None

    suburb_obj = None
    if inquiry.suburb:
        suburb_obj = (
            RegionSuburb.objects
            .filter(region=region, name=inquiry.suburb, is_active=True)
            .first()
        )

    if not suburb_obj:
        return None

    config = build_config_from_rule(suburb_obj, rule)
    booking = inquiry_to_pricing(inquiry, rule)
    result = calculate_price(config, booking)
    return str(result["total"])
