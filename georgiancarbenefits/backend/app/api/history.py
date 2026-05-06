from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.calculation import Calculation
from app.models.user import User
from app.schemas.calculator import CalculationOut, CalculatorRequest
from app.services import currency, customs, recycling
from app.services.learned_vehicle_power import remember_learned_vehicle_power
from app.services.personal_import_customs import calculatePersonalImportCustoms

router = APIRouter(prefix="/history", tags=["history"])


def _can_use_precise_personal_import(payload: CalculatorRequest) -> bool:
    if payload.is_personal_use is not True or payload.horse_power is None:
        return False
    return True


@router.post("/", response_model=CalculationOut, status_code=status.HTTP_201_CREATED)
async def save_calculation(
    payload: CalculatorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rates = await currency.get_rates()
    usd_to_rub = rates["USD"]
    eur_to_rub = rates["EUR"]
    gel_to_rub = rates["GEL"]

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
        duty = precise["unifiedRate"]
        rec = precise["utilFee"]
        stored_util_coefficient = precise["utilCoefficient"]
        total = round(
            payload.car_price_usd * usd_to_rub + precise["customsFee"] + duty + rec + payload.logistics_cost_rub,
            2,
        )
    else:
        usd_to_eur = eur_to_rub / usd_to_rub

        duty = customs.calculate_customs_duty(
            price_usd=payload.car_price_usd,
            engine_cc=payload.engine_volume_cc,
            car_year=payload.car_year,
            usd_to_eur=usd_to_eur,
            eur_to_rub=eur_to_rub,
        )
        rec = recycling.calculate_recycling_fee(payload.engine_volume_cc, payload.car_year)
        stored_util_coefficient = None
        total = round(
            payload.car_price_usd * usd_to_rub + duty + rec + payload.logistics_cost_rub, 2
        )

    calc = Calculation(
        user_id=current_user.id,
        car_price_usd=payload.car_price_usd,
        engine_volume_cc=payload.engine_volume_cc,
        car_year=payload.car_year,
        horse_power=payload.horse_power,
        util_coefficient=stored_util_coefficient,
        powertrain_kind=payload.powertrain_kind,
        power_kw_override=None,
        is_personal_use=payload.is_personal_use,
        logistics_cost_rub=payload.logistics_cost_rub,
        rf_analog_price_rub=payload.rf_analog_price_rub,
        customs_duty_rub=duty,
        recycling_fee_rub=rec,
        total_cost_rub=total,
        usd_to_rub=usd_to_rub,
        eur_to_rub=eur_to_rub,
        gel_to_rub=gel_to_rub,
        note=payload.note,
    )
    remember_learned_vehicle_power(
        db,
        make=payload.source_make,
        model=payload.source_model,
        model_id=payload.source_model_id,
        horse_power=payload.horse_power,
    )
    db.add(calc)
    db.commit()
    db.refresh(calc)
    return calc


@router.get("/", response_model=list[CalculationOut])
def list_calculations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Calculation)
        .filter(Calculation.user_id == current_user.id)
        .order_by(Calculation.created_at.desc())
        .all()
    )


@router.delete("/{calc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calculation(
    calc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    calc = (
        db.query(Calculation)
        .filter(Calculation.id == calc_id, Calculation.user_id == current_user.id)
        .first()
    )
    if not calc:
        raise HTTPException(status_code=404, detail="Calculation not found")
    db.delete(calc)
    db.commit()
