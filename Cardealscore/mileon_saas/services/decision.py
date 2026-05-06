from __future__ import annotations

from dataclasses import dataclass

from mileon_saas.config import settings
from mileon_saas.services.common import clamp


@dataclass
class DecisionResult:
    buy_score: float
    decision: str


def compute_buy_score(
    roi_percent: float,
    deal_score: float,
    liquidity_score: float,
    risk_score: float,
) -> float:
    roi_score = clamp(roi_percent / 30.0) * 100.0
    risk_safety = clamp(risk_score / 100.0) * 100.0

    return (
        0.40 * roi_score
        + 0.25 * deal_score
        + 0.20 * liquidity_score
        + 0.15 * risk_safety
    )


def decide_buy(
    buy_score: float,
    roi_percent: float,
    risk_score: float,
    ml_confidence: float,
    min_roi_required: float,
    blacklist_blocked: bool,
) -> DecisionResult:
    if (
        buy_score >= 90
        and roi_percent >= min_roi_required
        and risk_score >= 75
        and not blacklist_blocked
        and ml_confidence >= settings.ml_confidence_threshold
    ):
        return DecisionResult(buy_score=buy_score, decision="BUY WITHOUT DOUBT")

    if buy_score >= 75 and roi_percent >= min_roi_required and risk_score >= 60 and not blacklist_blocked:
        return DecisionResult(buy_score=buy_score, decision="BUY NOW")

    if buy_score >= 60:
        return DecisionResult(buy_score=buy_score, decision="CONSIDER")

    return DecisionResult(buy_score=buy_score, decision="SKIP")
