from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from mileon_saas.services.common import clamp, condition_score, expected_mileage
from mileon_saas.services.risk import RiskResult, evaluate_risk


@dataclass
class DealScoreResult:
    deal_score: float
    price_score: float
    mileage_score: float
    liquidity_score: float
    condition_score: float
    risk_score: float
    risk_flags: list[str]
    blacklist_blocked: bool


def price_score(price_usd: Optional[float], median_price: Optional[float]) -> float:
    if not price_usd or not median_price or median_price <= 0:
        return 0.5

    ratio = price_usd / median_price
    if ratio <= 0.85:
        return 1.0
    if ratio >= 1.15:
        return 0.0

    return clamp(1.0 - (ratio - 0.85) / 0.30)


def mileage_score(mileage_km: Optional[int], year: Optional[int]) -> float:
    expected = expected_mileage(year)
    if mileage_km is None or expected is None or expected <= 0:
        return 0.5

    deviation = abs(mileage_km - expected) / expected
    return clamp(1.0 - deviation)


def liquidity_score(multiplier: Optional[float]) -> float:
    if multiplier is None:
        return 0.5
    return clamp(multiplier / 1.2)


def compute_deal_score(
    listing,
    market_stats,
    brand_policy,
    blacklists,
) -> DealScoreResult:
    median_price = getattr(market_stats, "median_price_usd", None) if market_stats else None
    liquidity_multiplier = getattr(brand_policy, "liquidity_multiplier", None) if brand_policy else None

    price_val = price_score(getattr(listing, "price_usd", None), median_price)
    mileage_val = mileage_score(getattr(listing, "mileage_km", None), getattr(listing, "year", None))
    liquidity_val = liquidity_score(liquidity_multiplier)
    condition_val = condition_score(getattr(listing, "accident_history", None))

    risk_result: RiskResult = evaluate_risk(listing, blacklists)
    risk_val = clamp(risk_result.risk_score / 100.0)

    deal_score = (
        0.40 * price_val
        + 0.20 * mileage_val
        + 0.15 * liquidity_val
        + 0.15 * condition_val
        + 0.10 * risk_val
    ) * 100.0

    return DealScoreResult(
        deal_score=deal_score,
        price_score=price_val * 100.0,
        mileage_score=mileage_val * 100.0,
        liquidity_score=liquidity_val * 100.0,
        condition_score=condition_val * 100.0,
        risk_score=risk_result.risk_score,
        risk_flags=risk_result.flags,
        blacklist_blocked=risk_result.blacklist_blocked,
    )
