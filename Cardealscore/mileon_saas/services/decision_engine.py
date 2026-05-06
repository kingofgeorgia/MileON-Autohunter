from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.config import settings
from mileon_saas.models import BrandPolicy, CarListing, MarketStats, TechnicalBlacklist
from mileon_saas.schemas import ListingScores
from mileon_saas.services.decision import decide_buy, compute_buy_score
# ML temporarily on hold
# from mileon_saas.services.ml import confidence as ml_confidence_score
# from mileon_saas.services.ml import load_model, predict_price
from mileon_saas.services.pricing import compute_pricing
from mileon_saas.services.scoring import compute_deal_score


# ML feature building - temporarily disabled
# # ML feature building - temporarily disabled
# def _build_ml_features(listing: CarListing, market_stats: Optional[MarketStats], deal_result) -> dict:
#     median_price = market_stats.median_price_usd if market_stats else None
#     expected = expected_mileage(listing.year)
#     mileage_deviation = 0.0
#     if expected and listing.mileage_km is not None and expected > 0:
#         mileage_deviation = (listing.mileage_km - expected) / expected
# 
#     price_vs_market = 0.0
#     if median_price and listing.price_usd:
#         price_vs_market = (listing.price_usd - median_price) / median_price
# 
#     return {
#         "brand": listing.brand,
#         "model": listing.model,
#         "engine_type": listing.engine_type,
#         "transmission": listing.transmission,
#         "drivetrain": listing.drivetrain,
#         "imported_from": listing.imported_from,
#         "accident_history": listing.accident_history,
#         "year": listing.year or 0,
#         "mileage_km": listing.mileage_km or 0,
#         "owners_count": listing.owners_count or 0,
#         "mileage_deviation": mileage_deviation,
#         "price_vs_market": price_vs_market,
#         "liquidity_score": deal_result.liquidity_score,
#         "condition_score": condition_score(listing.accident_history),
#     }


async def evaluate_listing(session: AsyncSession, listing: CarListing) -> ListingScores:
    market_stats = await session.scalar(
        select(MarketStats).where(
            MarketStats.company_id == listing.company_id,
            MarketStats.brand == listing.brand,
            MarketStats.model == listing.model,
            MarketStats.year == listing.year,
        )
    )
    brand_policy = await session.scalar(
        select(BrandPolicy).where(
            BrandPolicy.company_id == listing.company_id,
            BrandPolicy.brand == listing.brand,
        )
    )
    blacklists = (await session.scalars(
        select(TechnicalBlacklist).where(
            TechnicalBlacklist.company_id == listing.company_id,
            TechnicalBlacklist.brand == listing.brand,
        )
    )).all()

    deal_result = compute_deal_score(listing, market_stats, brand_policy, blacklists)
    pricing = compute_pricing(listing, market_stats, deal_result.liquidity_score, brand_policy)

    # ML temporarily on hold
    # ml_bundle = load_model()
    # ml_confidence = ml_confidence_score(ml_bundle)
    ml_confidence = 0.0
    ml_expected_price = None
    # if ml_bundle:
    #     features = _build_ml_features(listing, market_stats, deal_result)
    #     ml_expected_price = predict_price(ml_bundle, features)
    #     if ml_confidence >= settings.ml_confidence_threshold:
    #         pricing = compute_pricing(
    #             listing,
    #             market_stats,
    #             deal_result.liquidity_score,
    #             brand_policy,
    #             repair_cost=0.0,
    #             tax_rate=0.02,
    #             expected_sell_override=ml_expected_price,
    #         )

    buy_score = compute_buy_score(
        pricing.roi_percent,
        deal_result.price_score,
        deal_result.liquidity_score,
        deal_result.data_confidence_score,
        target_roi_percent=brand_policy.min_roi_required if brand_policy else 15.0,
    )
    min_roi_required = brand_policy.min_roi_required if brand_policy else 12.0
    decision = decide_buy(
        buy_score,
        pricing.roi_percent,
        deal_result.risk_score,
        min_roi_required,
        deal_result.blacklist_blocked,
        deal_result.liquidity_score,
        deal_result.data_confidence_score,
        pricing.net_profit,
    )

    return ListingScores(
        deal_score=deal_result.deal_score,
        buy_score=decision.buy_score,
        price_score=deal_result.price_score,
        mileage_score=deal_result.mileage_score,
        liquidity_score=deal_result.liquidity_score,
        condition_score=deal_result.condition_score,
        data_confidence_score=deal_result.data_confidence_score,
        risk_score=deal_result.risk_score,
        expected_sell_price=pricing.expected_sell_price,
        ml_expected_price=ml_expected_price,
        net_profit=pricing.net_profit,
        roi_percent=pricing.roi_percent,
        expected_hold_days=pricing.expected_hold_days,
        decision=decision.decision,
        ml_confidence=ml_confidence,
        risk_flags=deal_result.risk_flags,
        blacklist_blocked=deal_result.blacklist_blocked,
    )
