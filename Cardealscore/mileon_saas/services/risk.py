from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from mileon_saas.services.common import expected_mileage


@dataclass
class RiskResult:
    risk_score: float
    flags: list[str]
    blacklist_blocked: bool


def evaluate_risk(listing, blacklists: Optional[Iterable]) -> RiskResult:
    penalty = 0.0
    flags: list[str] = []
    blacklist_blocked = False

    imported_from = getattr(listing, "imported_from", None)
    accident_history = getattr(listing, "accident_history", None)

    if imported_from and imported_from.lower() == "usa" and accident_history in {"cosmetic", "structural"}:
        flags.append("usa_import_with_damage")
        penalty += 0.15

    if accident_history == "structural":
        flags.append("structural_accident")
        penalty += 0.35

    if not getattr(listing, "vin", None):
        flags.append("missing_vin")
        penalty += 0.10

    mileage_km = getattr(listing, "mileage_km", None)
    year = getattr(listing, "year", None)
    expected = expected_mileage(year)
    if mileage_km is not None and expected and expected > 0:
        if mileage_km < expected * 0.5:
            flags.append("suspicious_low_mileage")
            penalty += 0.10

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
