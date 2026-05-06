from datetime import datetime

from pydantic import BaseModel

from app.services.personal_import_customs import PowertrainKind


class CalculatorRequest(BaseModel):
    car_price_usd: float
    engine_volume_cc: int
    car_year: int
    horse_power: float
    source_make: str | None = None
    source_model: str | None = None
    source_model_id: int | None = None
    powertrain_kind: PowertrainKind | None = None
    is_personal_use: bool = True
    logistics_cost_rub: float = 170_000.0
    rf_analog_price_rub: float | None = None
    note: str | None = None


class CurrencyRates(BaseModel):
    usd_to_rub: float
    eur_to_rub: float
    gel_to_rub: float


class CalculatorResult(BaseModel):
    car_price_rub: float
    customs_fee_rub: float | None = None
    customs_duty_rub: float
    recycling_fee_rub: float
    logistics_cost_rub: float
    total_cost_rub: float
    savings_vs_rf_rub: float | None = None
    rates: CurrencyRates


class CalculationOut(BaseModel):
    id: int
    car_price_usd: float
    engine_volume_cc: int
    car_year: int
    horse_power: float | None = None
    util_coefficient: float | None = None
    powertrain_kind: PowertrainKind | None = None
    is_personal_use: bool = True
    logistics_cost_rub: float
    rf_analog_price_rub: float | None
    customs_duty_rub: float
    recycling_fee_rub: float
    total_cost_rub: float
    usd_to_rub: float
    eur_to_rub: float
    gel_to_rub: float
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
