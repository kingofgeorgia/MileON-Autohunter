from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Optional

from mileon_saas.services.common import clamp, condition_score, expected_mileage


@dataclass
class PricingResult:
    expected_sell_price: float
    expected_hold_days: int
    hold_cost: float
    net_profit: float
    roi_percent: float


_PRICING_CACHE: dict[str, object] = {"mtime": None, "data": {}}


def _load_pricing_overrides() -> dict[str, float]:
    path = Path("ui_settings.json")
    if not path.exists():
        return {}

    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}

    if _PRICING_CACHE.get("mtime") == mtime:
        return _PRICING_CACHE.get("data", {})  # type: ignore[return-value]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    def as_float(key: str) -> Optional[float]:
        value = payload.get(key)
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    overrides = {
        "repair_cost": as_float("repair_cost"),
        "tax_rate": as_float("tax_rate"),
        "monthly_capital_rate": as_float("monthly_capital_rate"),
        "parking_daily": as_float("parking_daily"),
        "insurance_daily": as_float("insurance_daily"),
    }

    _PRICING_CACHE["mtime"] = mtime
    _PRICING_CACHE["data"] = overrides
    return overrides


def expected_sell_price(
    listing,
    market_stats,
    liquidity_score_value: float,
) -> float:
    base_price = 0.0
    if market_stats and market_stats.median_price_usd:
        base_price = market_stats.median_price_usd
    elif listing.price_usd:
        base_price = listing.price_usd

    if base_price <= 0:
        return 0.0

    price = base_price

    expected = expected_mileage(getattr(listing, "year", None))
    mileage_km = getattr(listing, "mileage_km", None)
    if expected and mileage_km is not None and expected > 0:
        deviation = (expected - mileage_km) / expected
        mileage_adjust = clamp(deviation * 0.10, -0.10, 0.10)
        price *= 1.0 + mileage_adjust

    condition = condition_score(getattr(listing, "accident_history", None))
    price *= 0.90 + condition * 0.15

    price *= 0.90 + (liquidity_score_value / 100.0) * 0.20

    return max(price, 0.0)


def compute_hold_cost(
    purchase_price: float,
    expected_hold_days: int,
    monthly_capital_rate: float = 0.025,
    parking_daily: float = 4.0,
    insurance_daily: float = 2.0,
) -> float:
    daily_capital = purchase_price * (monthly_capital_rate / 30.0)
    daily_total = daily_capital + parking_daily + insurance_daily
    return daily_total * expected_hold_days


def compute_pricing(
    listing,
    market_stats,
    liquidity_score_value: float,
    brand_policy,
    repair_cost: float = 0.0,
    tax_rate: float = 0.02,
    expected_sell_override: Optional[float] = None,
) -> PricingResult:
    hold_days = brand_policy.max_hold_days if brand_policy else 45
    expected_price = expected_sell_override
    if expected_price is None:
        expected_price = expected_sell_price(listing, market_stats, liquidity_score_value)

    purchase_price = float(getattr(listing, "price_usd", 0.0) or 0.0)
    overrides = _load_pricing_overrides()
    if overrides.get("repair_cost") is not None:
        repair_cost = overrides["repair_cost"]  # type: ignore[assignment]
    if overrides.get("tax_rate") is not None:
        tax_rate = overrides["tax_rate"]  # type: ignore[assignment]

    monthly_capital_rate = overrides.get("monthly_capital_rate") or 0.025
    parking_daily = overrides.get("parking_daily") or 4.0
    insurance_daily = overrides.get("insurance_daily") or 2.0

    hold_cost = compute_hold_cost(
        purchase_price,
        hold_days,
        monthly_capital_rate=monthly_capital_rate,
        parking_daily=parking_daily,
        insurance_daily=insurance_daily,
    )
    taxes = expected_price * tax_rate

    net_profit = expected_price - purchase_price - repair_cost - taxes - hold_cost
    roi_percent = (net_profit / purchase_price * 100.0) if purchase_price > 0 else 0.0

    return PricingResult(
        expected_sell_price=expected_price,
        expected_hold_days=hold_days,
        hold_cost=hold_cost,
        net_profit=net_profit,
        roi_percent=roi_percent,
    )
