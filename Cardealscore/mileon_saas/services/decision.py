from __future__ import annotations

from dataclasses import dataclass

from mileon_saas.services.common import clamp


@dataclass
class DecisionResult:
    buy_score: float
    decision: str


def compute_buy_score(
    roi_percent: float,
    price_score: float,
    liquidity_score: float,
    data_confidence_score: float,
    target_roi_percent: float = 15.0,
) -> float:
    roi_score = clamp(roi_percent / max(target_roi_percent, 1.0)) * 100.0

    return (
        0.45 * roi_score
        + 0.25 * liquidity_score
        + 0.20 * price_score
        + 0.10 * data_confidence_score
    )


def decide_buy(
    buy_score: float,
    roi_percent: float,
    risk_score: float,
    min_roi_required: float,
    blacklist_blocked: bool,
    liquidity_score: float,
    data_confidence_score: float,
    net_profit: float,
) -> DecisionResult:
    if blacklist_blocked:
        return DecisionResult(buy_score=buy_score, decision="BLOCKED")

    if net_profit <= 0 or roi_percent < min_roi_required * 0.6:
        return DecisionResult(buy_score=buy_score, decision="SKIP")

    if risk_score < 60:
        if roi_percent >= min_roi_required and buy_score >= 60:
            return DecisionResult(buy_score=buy_score, decision="CALL_SELLER")
        return DecisionResult(buy_score=buy_score, decision="WATCH")

    if (
        buy_score >= 75
        and roi_percent >= min_roi_required
        and liquidity_score >= 50
        and risk_score >= 70
        and data_confidence_score >= 45
    ):
        return DecisionResult(buy_score=buy_score, decision="GO_CHECK")

    if roi_percent >= min_roi_required and buy_score >= 60:
        return DecisionResult(buy_score=buy_score, decision="CALL_SELLER")

    if buy_score >= 50:
        return DecisionResult(buy_score=buy_score, decision="WATCH")

    return DecisionResult(buy_score=buy_score, decision="SKIP")
