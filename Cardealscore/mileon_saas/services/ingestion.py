import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.config import settings
from mileon_saas.models import CarListing


def _load_json(path: str) -> list[dict]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


_MAN_MODEL_INDEX: dict[int, dict[int, str]] | None = None
_MAN_NAME_INDEX: dict[int, str] | None = None


def _load_model_index() -> dict[int, dict[int, str]]:
    global _MAN_MODEL_INDEX, _MAN_NAME_INDEX
    if _MAN_MODEL_INDEX is not None:
        return _MAN_MODEL_INDEX

    mans_path = Path("mansNModels.json")
    if not mans_path.exists():
        mans_path = Path(__file__).resolve().parents[2] / "mansNModels.json"
    if not mans_path.exists():
        _MAN_MODEL_INDEX = {}
        _MAN_NAME_INDEX = {}
        return _MAN_MODEL_INDEX

    data = json.loads(mans_path.read_text(encoding="utf-8"))
    index: dict[int, dict[int, str]] = {}
    names: dict[int, str] = {}
    for man_id, man_data in data.items():
        try:
            man_key = int(man_id)
        except (TypeError, ValueError):
            continue
        make_name = str(man_data.get("make_name") or "").strip()
        if make_name:
            names[man_key] = make_name
        models = man_data.get("models", [])
        model_map: dict[int, str] = {}
        for model in models:
            model_id = model.get("model_id")
            model_name = model.get("model")
            if isinstance(model_id, int) and model_name:
                model_map[model_id] = model_name
        if model_map:
            index[man_key] = model_map

    _MAN_MODEL_INDEX = index
    _MAN_NAME_INDEX = names
    return _MAN_MODEL_INDEX


def _get_model_by_id(man_id: int | None, model_id: int | None) -> str | None:
    if not isinstance(man_id, int) or not isinstance(model_id, int):
        return None
    index = _load_model_index()
    return index.get(man_id, {}).get(model_id)


def _get_make_by_id(man_id: int | None) -> str | None:
    if not isinstance(man_id, int):
        return None
    _load_model_index()
    return (_MAN_NAME_INDEX or {}).get(man_id)


def _map_record(record: dict, company_id: int) -> tuple[dict, dict]:
    man_id = record.get("man_id")
    model_id = record.get("model_id")
    model_from_id = _get_model_by_id(man_id, model_id)

    model_source = "model_id" if model_from_id else ""
    model = model_from_id or record.get("model") or ""

    if not model:
        trim = record.get("trim", "")
        if trim:
            first_word = trim.split()[0] if trim.split() else ""
            model = first_word if first_word else "unknown"
            model_source = "trim"
        else:
            model = "unknown"
            model_source = "unknown"
    elif not model_source:
        model_source = "record"

    incoming_metadata = record.get("metadata") or record.get("listing_metadata") or {}
    if not isinstance(incoming_metadata, dict):
        incoming_metadata = {}

    meta = {
        **incoming_metadata,
        "car_id": record.get("car_id"),
        "man_id": man_id,
        "model_id": model_id,
        "make_name": record.get("make_name"),
        "model": model,
        "trim": record.get("trim"),
        "model_source": model_source,
        "pic_number": record.get("pic_number") or incoming_metadata.get("pic_number"),
        "price_value": record.get("price_value") or incoming_metadata.get("price_value"),
        "fuel_type_id": record.get("fuel_type_id") or record.get("fuel_type") or incoming_metadata.get("fuel_type_id"),
        "gear_type_id": record.get("gear_type_id") or incoming_metadata.get("gear_type_id"),
        "drive_type_id": record.get("drive_type_id") or incoming_metadata.get("drive_type_id"),
        "category_id": record.get("category_id") or record.get("category") or incoming_metadata.get("category_id"),
        "tech_inspection": record.get("tech_inspection") if "tech_inspection" in record else incoming_metadata.get("tech_inspection"),
        "predicted_price": record.get("predicted_price") or incoming_metadata.get("predicted_price"),
        "pred_min_price": record.get("pred_min_price") or incoming_metadata.get("pred_min_price"),
        "pred_max_price": record.get("pred_max_price") or incoming_metadata.get("pred_max_price"),
        "views": record.get("views") or incoming_metadata.get("views"),
        "daily_views": record.get("daily_views") or incoming_metadata.get("daily_views"),
        "order_date": record.get("order_date") or record.get("date") or incoming_metadata.get("order_date"),
        "changable": record.get("changable") if "changable" in record else incoming_metadata.get("changable"),
        "for_rent": record.get("for_rent") if "for_rent" in record else incoming_metadata.get("for_rent"),
        "rent_daily": record.get("rent_daily") if "rent_daily" in record else incoming_metadata.get("rent_daily"),
        "rent_purchase": record.get("rent_purchase") if "rent_purchase" in record else incoming_metadata.get("rent_purchase"),
    }

    return {
        "company_id": company_id,
        "source": "myauto",
        "source_listing_id": str(record.get("car_id")) if record.get("car_id") else None,
        
        # Basic info
        "brand": record.get("make_name") or _get_make_by_id(man_id) or "unknown",
        "model": model,
        "year": record.get("year") or record.get("prod_year"),
        
        # Engine
        "engine_type": None,
        "engine_code": None,
        "engine_volume": record.get("engine_volume"),
        "cylinders": record.get("cylinders"),
        
        # Transmission and drivetrain
        "transmission": None,
        "transmission_code": None,
        "drivetrain": None,
        
        # Body
        "doors": record.get("doors"),
        "color": record.get("color"),
        
        # Mileage and price
        "mileage_km": record.get("mileage_km") or record.get("car_run_km"),
        "price_usd": record.get("price_usd"),
        
        # History and condition
        "owners_count": record.get("owners_count"),
        "accident_history": record.get("accident_history"),
        "imported_from": record.get("imported_from"),
        "customs_passed": record.get("customs_passed"),
        
        # Identification
        "vin": record.get("vin"),
        "car_id": record.get("car_id"),
        
        # Location and status
        "location_id": record.get("location_id"),
        "status_id": record.get("status_id"),
        "user_id": record.get("user_id"),
        "dealer_user_id": record.get("dealer_user_id"),
        
        # Media and description
        "photo_url": record.get("photo_url"),
        "description": record.get("description") or record.get("car_desc"),
        
        # Timestamps
        "listing_date": record.get("date") or record.get("order_date"),
        
        # Features and metadata (JSON fields)
        "features": record.get("features"),
        "listing_metadata": meta,
    }, meta


async def ingest_from_json(session: AsyncSession, path: str, company_id: int | None = None) -> int:
    company_id = company_id or settings.default_company_id
    payload = _load_json(path)
    if not payload:
        return 0

    new_count = 0
    skipped_no_price = 0
    skipped_bargain_type = 0
    unknown_models: list[dict] = []
    batch_size = 100  # Commit in batches for better performance on large files
    
    for idx, record in enumerate(payload):
        mapped, meta = _map_record(record, company_id)
        
        # Skip listings with bargainType=1 (apply same filter as parser)
        if record.get("bargainType") == 1:
            skipped_bargain_type += 1
            continue
        
        # Skip listings without valid price
        price_usd = mapped.get("price_usd")
        if price_usd is None or price_usd == 0:
            skipped_no_price += 1
            continue
        
        source_id = mapped.get("source_listing_id")
        if source_id:
            existing = await session.scalar(
                select(CarListing).where(
                    CarListing.company_id == company_id,
                    CarListing.source == "myauto",
                    CarListing.source_listing_id == source_id,
                )
            )
            if existing:
                continue

        if meta.get("model_source") in {"trim", "unknown"}:
            unknown_models.append(meta)

        session.add(CarListing(**mapped))
        new_count += 1
        
        # Batch commit every N records for better performance
        if (idx + 1) % batch_size == 0:
            await session.commit()

    # Final commit for remaining records
    await session.commit()
    
    # Log summary
    if skipped_bargain_type > 0:
        print(f"Ingestion: Skipped {skipped_bargain_type} listings with bargainType=1")
    if skipped_no_price > 0:
        print(f"Ingestion: Skipped {skipped_no_price} listings without price")
    
    if unknown_models:
        output = {
            "generated_at": datetime.utcnow().isoformat(),
            "count": len(unknown_models),
            "items": unknown_models,
        }
        Path("unknown_models.json").write_text(
            json.dumps(output, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
    return new_count
