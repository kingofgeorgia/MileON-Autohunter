import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.learned_vehicle_power import LearnedVehiclePower


logger = logging.getLogger(__name__)


def normalize_vehicle_lookup_value(value: str | None) -> str:
    return " ".join(str(value or "").lower().split())


def find_learned_vehicle_power(
    db: Session,
    *,
    make: str | None,
    model: str | None,
    model_id: int | None,
) -> LearnedVehiclePower | None:
    try:
        if model_id:
            record = (
                db.query(LearnedVehiclePower)
                .filter(LearnedVehiclePower.model_id == model_id)
                .order_by(LearnedVehiclePower.updated_at.desc(), LearnedVehiclePower.id.desc())
                .first()
            )
            if record:
                return record

        normalized_make = normalize_vehicle_lookup_value(make)
        normalized_model = normalize_vehicle_lookup_value(model)
        if not normalized_make or not normalized_model:
            return None

        return (
            db.query(LearnedVehiclePower)
            .filter(
                LearnedVehiclePower.normalized_make == normalized_make,
                LearnedVehiclePower.normalized_model == normalized_model,
            )
            .order_by(LearnedVehiclePower.updated_at.desc(), LearnedVehiclePower.id.desc())
            .first()
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to read learned vehicle horsepower; continuing without DB-backed fallback")
        return None


def remember_learned_vehicle_power(
    db: Session,
    *,
    make: str | None,
    model: str | None,
    model_id: int | None,
    horse_power: float | None,
) -> LearnedVehiclePower | None:
    if horse_power is None or horse_power <= 0:
        return None

    normalized_make = normalize_vehicle_lookup_value(make)
    normalized_model = normalize_vehicle_lookup_value(model)
    if not normalized_make or not normalized_model:
        return None

    try:
        record = find_learned_vehicle_power(
            db,
            make=make,
            model=model,
            model_id=model_id,
        )
        if record is None:
            record = LearnedVehiclePower(
                make=str(make).strip(),
                model=str(model).strip(),
                normalized_make=normalized_make,
                normalized_model=normalized_model,
                model_id=model_id,
                horse_power=horse_power,
            )
        else:
            record.make = str(make).strip()
            record.model = str(model).strip()
            record.normalized_make = normalized_make
            record.normalized_model = normalized_model
            record.model_id = model_id
            record.horse_power = horse_power

        db.add(record)
        db.flush()
        return record
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to persist learned vehicle horsepower; continuing without DB-backed memory")
        return None