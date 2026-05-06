from datetime import datetime
from typing import Any, Optional


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def expected_mileage(year: Optional[int]) -> Optional[int]:
    if not year:
        return None
    current_year = datetime.utcnow().year
    age = max(current_year - year, 0)
    return age * 15000


def listing_metadata(listing) -> dict[str, Any]:
    metadata = getattr(listing, "listing_metadata", None) or {}
    return metadata if isinstance(metadata, dict) else {}


def metadata_value(listing, *keys: str) -> Any:
    metadata = listing_metadata(listing)
    for key in keys:
        if key in metadata and metadata[key] not in (None, ""):
            return metadata[key]
    return None


def listing_date(listing) -> Optional[datetime]:
    raw_value = getattr(listing, "listing_date", None) or metadata_value(
        listing,
        "order_date",
        "date",
    )
    if not raw_value:
        return None

    value = str(raw_value).strip()
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    return None


def listing_age_days(listing, now: Optional[datetime] = None) -> Optional[int]:
    parsed = listing_date(listing)
    if not parsed:
        return None
    now = now or datetime.utcnow()
    return max((now - parsed).days, 0)


def predicted_price_usd(listing) -> Optional[float]:
    predicted = as_float(metadata_value(listing, "predicted_price"))
    if not predicted or predicted <= 0:
        return None

    listing_price_usd = as_float(getattr(listing, "price_usd", None))
    price_value = as_float(metadata_value(listing, "price_value"))
    if listing_price_usd and price_value and price_value > 0:
        inferred_fx = price_value / listing_price_usd
        if 1.5 <= inferred_fx <= 4.5:
            return predicted / inferred_fx

    if listing_price_usd and 0.5 * listing_price_usd <= predicted <= 2.0 * listing_price_usd:
        return predicted
    return None


def market_reference_price_usd(listing, market_stats) -> Optional[float]:
    median = as_float(getattr(market_stats, "median_price_usd", None)) if market_stats else None
    predicted = predicted_price_usd(listing)

    if median and median > 0 and predicted and predicted > 0:
        return median * 0.75 + predicted * 0.25
    if median and median > 0:
        return median
    if predicted and predicted > 0:
        return predicted
    return None


def condition_score(accident_history: Optional[str]) -> float:
    mapping = {
        "none": 1.0,
        "cosmetic": 0.7,
        "structural": 0.3,
        "unknown": 0.5,
    }
    if not accident_history:
        return mapping["unknown"]
    return mapping.get(accident_history.lower(), mapping["unknown"])
