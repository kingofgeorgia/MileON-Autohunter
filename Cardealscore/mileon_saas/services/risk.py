from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from mileon_saas.services.common import (
    as_float,
    as_int,
    expected_mileage,
    listing_age_days,
    market_reference_price_usd,
    metadata_value,
)


@dataclass
class RiskResult:
    risk_score: float
    flags: list[str]
    blacklist_blocked: bool


def evaluate_risk(listing, blacklists: Optional[Iterable], market_stats=None) -> RiskResult:
    penalty = 0.0
    flags: list[str] = []
    blacklist_blocked = False

    price_usd = as_float(getattr(listing, "price_usd", None))
    year = as_int(getattr(listing, "year", None))
    engine_volume = as_int(getattr(listing, "engine_volume", None))
    reference_price = market_reference_price_usd(listing, market_stats)

    if not price_usd or price_usd <= 0:
        flags.append("missing_price")
        penalty += 0.30

    if not year:
        flags.append("missing_year_for_costing")
        penalty += 0.20

    if not engine_volume and not metadata_value(listing, "fuel_type_id"):
        flags.append("missing_engine_for_costing")
        penalty += 0.20

    if price_usd and reference_price and reference_price > 0:
        ratio = price_usd / reference_price
        if ratio < 0.70:
            flags.append("severe_price_anomaly")
            penalty += 0.15
        elif ratio < 0.80:
            flags.append("price_below_market_needs_check")
            penalty += 0.05
        elif ratio > 1.25:
            flags.append("overpriced_vs_market")
            penalty += 0.10

    mileage_km = getattr(listing, "mileage_km", None)
    expected = expected_mileage(year)
    if mileage_km is not None and expected and expected > 0:
        if mileage_km < 1000 and year and max(0, datetime.utcnow().year - year) >= 5:
            flags.append("very_low_mileage_needs_check")
            penalty += 0.08
        if mileage_km > expected * 2.5:
            flags.append("very_high_mileage")
            penalty += 0.10

    vin = getattr(listing, "vin", None)
    if vin:
        normalized_vin = str(vin).strip().upper()
        if len(normalized_vin) != 17:
            flags.append("vin_format_needs_check")
            penalty += 0.05

    age_days = listing_age_days(listing)
    views = as_int(metadata_value(listing, "views"))
    if age_days is not None and views is not None and age_days >= 60 and views >= 500:
        flags.append("old_listing_high_views")
        penalty += 0.10

    tech_inspection = metadata_value(listing, "tech_inspection")
    customs_passed = getattr(listing, "customs_passed", None)
    if customs_passed is True and tech_inspection in {False, 0}:
        flags.append("tech_inspection_false")
        penalty += 0.05

    if any(metadata_value(listing, key) is True for key in ("for_rent", "rent_daily", "rent_purchase")):
        flags.append("rental_listing")
        penalty += 0.40
        blacklist_blocked = True

    engine_code = getattr(listing, "engine_code", None)
    transmission_code = getattr(listing, "transmission_code", None)
    brand = getattr(listing, "brand", None)

    for entry in blacklists or []:
        if entry.brand != brand:
            continue
        if entry.component_type == "engine" and engine_code and entry.component_code == engine_code:
            flags.append("engine_blacklist")
            penalty += 0.30
            if entry.severity == "high":
                blacklist_blocked = True
        if entry.component_type == "transmission" and transmission_code and entry.component_code == transmission_code:
            flags.append("transmission_blacklist")
            penalty += 0.30
            if entry.severity == "high":
                blacklist_blocked = True

    risk_score = max(0.0, (1.0 - penalty)) * 100.0
    return RiskResult(risk_score=risk_score, flags=flags, blacklist_blocked=blacklist_blocked)
