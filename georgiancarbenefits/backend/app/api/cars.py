from datetime import date
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.cars import CarListing, CarModelOption
from app.services import currency, customs, myauto, recycling
from app.services.learned_vehicle_power import find_learned_vehicle_power
from app.services.personal_import_customs import calculatePersonalImportCustoms, horsePowerToKw, resolveUtilCoefficient2026PersonalM1

router = APIRouter(prefix="/cars", tags=["cars"])


def _can_use_precise_personal_import(car: CarListing) -> bool:
    return car.horse_power is not None


class CarUrlRequest(BaseModel):
    url: str


def _apply_learned_horse_power(db: Session, car: CarListing) -> CarListing:
    learned = find_learned_vehicle_power(
        db,
        make=car.make,
        model=car.model,
        model_id=car.model_id,
    )
    if learned is None or car.horse_power_source == "listing_hp":
        return car

    car.horse_power = int(round(float(learned.horse_power)))
    car.horse_power_source = "learned_db"

    if car.engine_volume_cc and car.year and car.horse_power:
        try:
            age_years = max(0, date.today().year - car.year)
            car.util_coefficient, _, _, _ = resolveUtilCoefficient2026PersonalM1(
                powertrain_kind=car.powertrain_kind or "ICE",
                age_years=age_years,
                power_kw=horsePowerToKw(float(car.horse_power)),
                engine_cc=car.engine_volume_cc,
            )
        except ValueError:
            pass

    return car


@router.get("/search", response_model=list[CarListing])
async def search(
    make_id: int | None = Query(None),
    model_id: int | None = Query(None),
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    price_usd_to: int | None = Query(None),
    page: int = Query(1, ge=1),
    logistics_cost_rub: float = Query(170_000.0),
    _: User = Depends(get_current_user),
):
    raw_list = await myauto.search_cars(
        make_id=make_id,
        model_id=model_id,
        year_from=year_from,
        year_to=year_to,
        price_usd_to=price_usd_to,
        page=page,
    )

    rates = await currency.get_rates()
    usd_to_rub = rates["USD"]
    eur_to_rub = rates["EUR"]

    result: list[CarListing] = []
    for raw in raw_list:
        car = myauto.parse_car(raw)
        if car.engine_volume_cc and car.year and car.price_usd:
            if _can_use_precise_personal_import(car):
                age_years = max(0, date.today().year - car.year)
                precise = calculatePersonalImportCustoms(
                    {
                        "price": car.price_usd,
                        "currencyToRubRate": usd_to_rub,
                        "eurToRubRate": eur_to_rub,
                        "engineCc": car.engine_volume_cc,
                        "horsePower": car.horse_power or 0,
                        "ageYears": age_years,
                        "isPersonalUse": True,
                        "powertrainKind": car.powertrain_kind,
                    }
                )
                total = round(car.price_usd * usd_to_rub + precise["total"] + logistics_cost_rub, 2)
            else:
                usd_to_eur = eur_to_rub / usd_to_rub
                duty = customs.calculate_customs_duty(
                    price_usd=car.price_usd,
                    engine_cc=car.engine_volume_cc,
                    car_year=car.year,
                    usd_to_eur=usd_to_eur,
                    eur_to_rub=eur_to_rub,
                )
                rec = recycling.calculate_recycling_fee(car.engine_volume_cc, car.year)
                total = round(car.price_usd * usd_to_rub + duty + rec + logistics_cost_rub, 2)
            car.estimated_total_rub = total
        result.append(car)

    return result


@router.get("/makes")
async def get_makes() -> list[Any]:
    return await myauto.get_makes()


@router.get("/models", response_model=list[CarModelOption])
async def get_models(
    make_id: int = Query(..., ge=1),
) -> list[CarModelOption]:
    return [CarModelOption(**item) for item in await myauto.get_models(make_id)]


@router.post("/from-url", response_model=CarListing)
async def car_from_url(
    payload: CarUrlRequest,
    db: Session = Depends(get_db),
):
    """Принять ссылку на авто с myauto.ge, вернуть данные авто."""
    match = re.search(r"/pr/(\d+)", payload.url.strip())
    if not match:
        raise HTTPException(status_code=422, detail="Некорректная ссылка myauto.ge. Ожидается формат: https://www.myauto.ge/.../pr/12345")
    car_id = int(match.group(1))
    raw = await myauto.get_car_by_id(car_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Автомобиль не найден на myauto.ge")
    return _apply_learned_horse_power(db, myauto.parse_car(raw))
