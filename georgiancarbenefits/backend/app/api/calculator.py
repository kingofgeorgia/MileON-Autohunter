from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.calculator import CalculatorRequest, CalculatorResult, CurrencyRates
from app.services import customs, currency, recycling
from app.services.learned_vehicle_power import remember_learned_vehicle_power
from app.services.personal_import_customs import calculatePersonalImportCustoms

router = APIRouter(prefix="/calculator", tags=["calculator"])


def _can_use_precise_personal_import(payload: CalculatorRequest) -> bool:
    if payload.is_personal_use is not True or payload.horse_power is None:
        return False
    return True


@router.post("/total", response_model=CalculatorResult)
async def calculate_total(
    payload: CalculatorRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rates = await currency.get_rates()
    usd_to_rub = rates["USD"]
    eur_to_rub = rates["EUR"]
    gel_to_rub = rates["GEL"]

    car_price_rub = round(payload.car_price_usd * usd_to_rub, 2)

    customs_fee_rub: float | None = None

    if _can_use_precise_personal_import(payload):
        age_years = max(0, date.today().year - payload.car_year)
        precise = calculatePersonalImportCustoms(
            {
                "price": payload.car_price_usd,
                "currencyToRubRate": usd_to_rub,
                "eurToRubRate": eur_to_rub,
                "engineCc": payload.engine_volume_cc,
                "horsePower": payload.horse_power or 0,
                "ageYears": age_years,
                "isPersonalUse": payload.is_personal_use,
                "powertrainKind": payload.powertrain_kind,
            }
        )
        customs_fee_rub = precise["customsFee"]
        duty_rub = precise["unifiedRate"]
        recycling_rub = precise["utilFee"]
        total = round(
            car_price_rub + customs_fee_rub + duty_rub + recycling_rub + payload.logistics_cost_rub,
            2,
        )
    else:
        usd_to_eur = eur_to_rub / usd_to_rub

        duty_rub = customs.calculate_customs_duty(
            price_usd=payload.car_price_usd,
            engine_cc=payload.engine_volume_cc,
            car_year=payload.car_year,
            usd_to_eur=usd_to_eur,
            eur_to_rub=eur_to_rub,
        )

        recycling_rub = recycling.calculate_recycling_fee(
            engine_cc=payload.engine_volume_cc,
            car_year=payload.car_year,
        )

        total = round(
            car_price_rub + duty_rub + recycling_rub + payload.logistics_cost_rub, 2
        )

    savings = None
    if payload.rf_analog_price_rub is not None:
        savings = round(payload.rf_analog_price_rub - total, 2)

    if payload.source_make and payload.source_model:
        remembered = remember_learned_vehicle_power(
            db,
            make=payload.source_make,
            model=payload.source_model,
            model_id=payload.source_model_id,
            horse_power=payload.horse_power,
        )
        if remembered is not None:
            db.commit()

    return CalculatorResult(
        car_price_rub=car_price_rub,
        customs_fee_rub=customs_fee_rub,
        customs_duty_rub=duty_rub,
        recycling_fee_rub=recycling_rub,
        logistics_cost_rub=payload.logistics_cost_rub,
        total_cost_rub=total,
        savings_vs_rf_rub=savings,
        rates=CurrencyRates(
            usd_to_rub=usd_to_rub,
            eur_to_rub=eur_to_rub,
            gel_to_rub=gel_to_rub,
        ),
    )


@router.get("/rates", response_model=CurrencyRates)
async def get_rates(_: User = Depends(get_current_user)):
    rates = await currency.get_rates()
    return CurrencyRates(
        usd_to_rub=rates["USD"],
        eur_to_rub=rates["EUR"],
        gel_to_rub=rates["GEL"],
    )
