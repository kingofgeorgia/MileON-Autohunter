from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from mileon_saas.services.common import (
    as_float,
    as_int,
    clamp,
    expected_mileage,
    listing_age_days,
    market_reference_price_usd,
    metadata_value,
)
from mileon_saas.services.risk import RiskResult, evaluate_risk


@dataclass
class DealScoreResult:
    deal_score: float
    price_score: float
    mileage_score: float
    liquidity_score: float
    condition_score: float
    data_confidence_score: float
    risk_score: float
    risk_flags: list[str]
    blacklist_blocked: bool


def price_score(price_usd: Optional[float], reference_price: Optional[float]) -> float:
    if not price_usd or not reference_price or reference_price <= 0:
        return 0.5

    ratio = price_usd / reference_price
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


def _market_depth_score(listings_count: Optional[int]) -> float:
    if listings_count is None:
        return 0.5
    if listings_count >= 40:
        return 0.9
    if listings_count >= 15:
        return 0.7
    if listings_count >= 5:
        return 0.45
    if listings_count >= 1:
        return 0.25
    return 0.2


def _views_demand_score(listing) -> float:
    daily_views = metadata_value(listing, "daily_views")
    if isinstance(daily_views, dict):
        value = as_float(daily_views.get("views"))
        if value is not None:
            if value >= 100:
                return 0.95
            if value >= 40:
                return 0.80
            if value >= 15:
                return 0.65
            if value >= 5:
                return 0.50
            return 0.30

    views = as_float(metadata_value(listing, "views"))
    age_days = listing_age_days(listing)
    if views is None or age_days is None:
        return 0.5
    views_per_day = views / max(age_days, 1)
    if views_per_day >= 30:
        return 0.90
    if views_per_day >= 10:
        return 0.75
    if views_per_day >= 3:
        return 0.55
    if views_per_day >= 1:
        return 0.40
    return 0.25


def _turnover_proxy_score(listing) -> float:
    age_days = listing_age_days(listing)
    if age_days is None:
        return 0.5
    if age_days <= 7:
        return 0.8
    if age_days <= 30:
        return 0.7
    if age_days <= 60:
        return 0.5
    if age_days <= 120:
        return 0.3
    return 0.15


def _brand_policy_score(multiplier: Optional[float]) -> float:
    if multiplier is None:
        return 0.5
    return clamp(multiplier / 1.2)


def liquidity_score(listing, market_stats, brand_policy) -> float:
    listings_count = as_int(getattr(market_stats, "listings_count", None)) if market_stats else None
    liquidity_multiplier = (
        as_float(getattr(brand_policy, "liquidity_multiplier", None)) if brand_policy else None
    )

    return clamp(
        0.30 * _market_depth_score(listings_count)
        + 0.25 * _views_demand_score(listing)
        + 0.25 * _turnover_proxy_score(listing)
        + 0.10 * 0.5
        + 0.10 * _brand_policy_score(liquidity_multiplier)
    )


def data_confidence_score(listing) -> float:
    score = 40.0

    mileage = getattr(listing, "mileage_km", None)
    engine_volume = getattr(listing, "engine_volume", None)
    fuel_type = metadata_value(listing, "fuel_type_id", "fuel_type")
    gear_type = metadata_value(listing, "gear_type_id")
    drive_type = metadata_value(listing, "drive_type_id")
    tech_inspection = metadata_value(listing, "tech_inspection")
    customs_passed = getattr(listing, "customs_passed", None)
    description = getattr(listing, "description", None) or ""
    pic_number = as_int(metadata_value(listing, "pic_number"))
    photo_url = getattr(listing, "photo_url", None)
    vin = getattr(listing, "vin", None)
    location = getattr(listing, "location_id", None)
    source_listing_id = getattr(listing, "source_listing_id", None)

    if mileage is not None:
        score += 10
    else:
        score -= 8

    if engine_volume:
        score += 10
    else:
        score -= 10

    if fuel_type:
        score += 6
    if gear_type:
        score += 4
    if drive_type:
        score += 4
    if tech_inspection in {True, 1}:
        score += 5
    if customs_passed is not None:
        score += 5

    description_length = len(str(description).strip())
    if description_length >= 250:
        score += 8
    elif description_length >= 80:
        score += 5
    elif description_length == 0:
        score -= 8

    if pic_number is not None:
        if pic_number >= 8:
            score += 8
        elif pic_number >= 4:
            score += 4
        elif pic_number < 2:
            score -= 5
    elif not photo_url:
        score -= 5

    if vin:
        score += 3
    if location:
        score += 4
    if source_listing_id:
        score += 5

    return clamp(score, 0.0, 100.0)


def compute_deal_score(
    listing,
    market_stats,
    brand_policy,
    blacklists,
) -> DealScoreResult:
    reference_price = market_reference_price_usd(listing, market_stats)

    price_val = price_score(getattr(listing, "price_usd", None), reference_price)
    mileage_val = mileage_score(getattr(listing, "mileage_km", None), getattr(listing, "year", None))
    liquidity_val = liquidity_score(listing, market_stats, brand_policy)
    data_confidence_val = data_confidence_score(listing) / 100.0

    risk_result: RiskResult = evaluate_risk(listing, blacklists, market_stats)

    deal_score = (
        0.45 * price_val
        + 0.25 * liquidity_val
        + 0.20 * mileage_val
        + 0.10 * data_confidence_val
    ) * 100.0

    return DealScoreResult(
        deal_score=deal_score,
        price_score=price_val * 100.0,
        mileage_score=mileage_val * 100.0,
        liquidity_score=liquidity_val * 100.0,
        condition_score=data_confidence_val * 100.0,
        data_confidence_score=data_confidence_val * 100.0,
        risk_score=risk_result.risk_score,
        risk_flags=risk_result.flags,
        blacklist_blocked=risk_result.blacklist_blocked,
    )
