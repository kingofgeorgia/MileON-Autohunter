from types import SimpleNamespace

from mileon_saas.services.decision import compute_buy_score, decide_buy
from mileon_saas.services.pricing import compute_pricing
from mileon_saas.services.risk import evaluate_risk
from mileon_saas.services.scoring import compute_deal_score, data_confidence_score


def _listing(**overrides):
    values = {
        "company_id": 1,
        "brand": "Toyota",
        "model": "Camry",
        "year": 2019,
        "engine_volume": 2500,
        "mileage_km": 90000,
        "price_usd": 12000.0,
        "vin": "",
        "customs_passed": True,
        "description": "Clean listing with enough seller details and service notes for a call.",
        "photo_url": "https://example.com/1.jpg",
        "source_listing_id": "123",
        "listing_date": "2026-05-01 10:00:00",
        "location_id": 2,
        "listing_metadata": {
            "fuel_type_id": 2,
            "gear_type_id": 3,
            "drive_type_id": 1,
            "pic_number": 10,
            "tech_inspection": True,
            "price_value": 32400,
            "views": 120,
            "daily_views": {"views": 25},
        },
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _market(**overrides):
    values = {
        "median_price_usd": 15000.0,
        "listings_count": 28,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _policy(**overrides):
    values = {
        "liquidity_multiplier": 1.0,
        "max_hold_days": 60,
        "min_roi_required": 12.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_missing_vin_is_data_confidence_not_hard_risk():
    listing = _listing(vin="")

    risk = evaluate_risk(listing, [], _market())
    confidence = data_confidence_score(listing)

    assert risk.risk_score >= 80
    assert "missing_vin" not in risk.flags
    assert confidence >= 70


def test_severe_price_anomaly_is_a_verifiable_risk_flag():
    listing = _listing(price_usd=9000.0)

    risk = evaluate_risk(listing, [], _market(median_price_usd=15000.0))

    assert "severe_price_anomaly" in risk.flags
    assert risk.risk_score < 90


def test_listing_only_pipeline_returns_check_or_call_action():
    listing = _listing(price_usd=11000.0)
    market = _market(median_price_usd=15000.0)
    policy = _policy(min_roi_required=8.0)

    deal = compute_deal_score(listing, market, policy, [])
    pricing = compute_pricing(listing, market, deal.liquidity_score, policy)
    buy_score = compute_buy_score(
        pricing.roi_percent,
        deal.price_score,
        deal.liquidity_score,
        deal.data_confidence_score,
        target_roi_percent=policy.min_roi_required,
    )
    decision = decide_buy(
        buy_score,
        pricing.roi_percent,
        deal.risk_score,
        policy.min_roi_required,
        deal.blacklist_blocked,
        deal.liquidity_score,
        deal.data_confidence_score,
        pricing.net_profit,
    )

    assert decision.decision in {"GO_CHECK", "CALL_SELLER"}
    assert decision.decision != "BUY NOW"
