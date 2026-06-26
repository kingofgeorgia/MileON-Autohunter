from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass
class EstimateRequest:
    car_price: float
    engine_volume: float = 2.0
    engine_power: int = 180
    year: int = 2018
    fuel_type: str = "petrol"
    customs_rate: float = 0.4
    logistics_cost: float = 0.0
    broker_fee: float = 0.0
    registration_cost: float = 0.0
    currency: str = "RUB"
    source_url: str | None = None


def _normalize_rate(rate: float | None, default: float) -> float:
    if rate is None:
        return default
    return max(0.1, min(0.8, float(rate)))


def estimate_import_cost(request: EstimateRequest) -> dict[str, Any]:
    customs_rate = _normalize_rate(getattr(request, "customs_rate", None), 0.4)
    car_price = max(0.0, float(request.car_price))
    engine_volume = max(0.1, float(request.engine_volume))
    engine_power = max(1, int(request.engine_power))
    year = max(1990, int(request.year))
    logistics_cost = max(0.0, float(getattr(request, "logistics_cost", 0.0)))
    broker_fee = max(0.0, float(getattr(request, "broker_fee", 0.0)))
    registration_cost = max(0.0, float(getattr(request, "registration_cost", 0.0)))

    if year < 2010:
        customs_rate = max(customs_rate, 0.5)
    elif year < 2015:
        customs_rate = max(customs_rate, 0.45)

    fuel_type = str(getattr(request, "fuel_type", "petrol")).lower()
    if fuel_type in {"electric", "ev", "hybrid"}:
        customs_rate = min(customs_rate, 0.2)

    customs_duty = car_price * customs_rate
    vat = (car_price + customs_duty + logistics_cost + broker_fee + registration_cost) * 0.2
    excise = engine_power * 15 + engine_volume * 500
    total_cost = car_price + customs_duty + vat + logistics_cost + broker_fee + registration_cost + excise

    return {
        "car_price": round(car_price, 2),
        "customs_rate": round(customs_rate, 3),
        "customs_duty": round(customs_duty, 2),
        "vat": round(vat, 2),
        "logistics_cost": round(logistics_cost, 2),
        "broker_fee": round(broker_fee, 2),
        "registration_cost": round(registration_cost, 2),
        "excise": round(excise, 2),
        "total_cost": round(total_cost, 2),
        "currency": getattr(request, "currency", "RUB"),
        "source_url": getattr(request, "source_url", None),
        "comparison_note": "Базовая модель расчёта, ориентированная на структуру Alta.ru: стоимость авто + таможня + НДС + логистика + брокер + оформление.",
    }


def parse_myauto_url(url: str | None) -> dict[str, Any]:
    result = {
        "source": "myauto.ge",
        "listing_id": None,
        "path": None,
        "query": {},
    }
    if not url:
        return result

    parsed = urlparse(url)
    result["path"] = parsed.path
    result["query"] = parse_qs(parsed.query)

    parts = [part for part in parsed.path.split("/") if part]
    for part in parts:
        if part.isdigit():
            result["listing_id"] = part
            break

    if not result["listing_id"]:
        query_values = result["query"]
        for key in ("id", "listing_id", "auto_id"):
            if key in query_values and query_values[key]:
                result["listing_id"] = query_values[key][0]
                break

    return result
