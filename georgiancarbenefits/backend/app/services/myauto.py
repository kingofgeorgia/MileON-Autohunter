"""
Сервис интеграции с myauto.ge API.
Документация: https://api2.myauto.ge (публичный, без ключа).
"""

from datetime import date
from importlib import import_module
from typing import Any

from app.core.config import settings
from app.schemas.cars import CarListing
from app.services.personal_import_customs import PowertrainKind, resolveUtilCoefficient2026PersonalM1
from app.services.vehicle_specs import resolve_vehicle_spec

_curl_requests = import_module("curl_cffi.requests")

_IMPERSONATE = "chrome120"
_mans_cache: dict[int, str] = {}
_models_cache: dict[int, dict[int, str]] = {}
_models_directory_cache: dict[int, list[dict[str, Any]]] = {}
_MYAUTO_IMAGE_BASE_URL = "https://static.my.ge/myauto/photos"
_SUV_CATEGORY_IDS = {5, 66}
_FUEL_TYPE_LABELS: dict[int, str] = {
    1: "Gas",
    2: "Petrol",
    3: "Diesel",
    4: "Hybrid",
    5: "CNG",
    6: "LPG",
    7: "Electric",
    8: "Hydrogen",
    9: "Plug-in hybrid",
}


def _resolve_fuel_type(raw: dict[str, Any]) -> str | None:
    fuel_type_id = int(raw.get("fuel_type_id", 0) or 0)
    if not fuel_type_id:
        return None
    return _FUEL_TYPE_LABELS.get(fuel_type_id, f"Fuel type #{fuel_type_id}")


def _resolve_powertrain_kind(
    raw: dict[str, Any], resolved_spec_powertrain_kind: PowertrainKind | None
) -> PowertrainKind:
    if resolved_spec_powertrain_kind:
        return resolved_spec_powertrain_kind

    fuel_type_id = int(raw.get("fuel_type_id", 0) or 0)
    if fuel_type_id == 7:
        return "EV"
    return "ICE"


async def _resolve_man_name(session: Any, man_id: int) -> str:
    """Возвращает название производителя по man_id, используя кеш."""
    global _mans_cache
    if not _mans_cache:
        try:
            r = await session.get(
                f"{settings.myauto_api_url}/vehicle/mans",
                params={"vehicle_types": "0.1.2"},
                headers={"Accept": "application/json"},
            )
            if r.status_code == 200:
                for m in r.json():
                    _mans_cache[int(m["man_id"])] = m["title"]
        except Exception:
            pass
    return _mans_cache.get(man_id, str(man_id))


async def _resolve_model_name(session: Any, man_id: int, model_id: int) -> str:
    """Возвращает название модели по man_id/model_id, используя кеш справочника."""
    if not man_id or not model_id:
        return ""

    models = _models_cache.get(man_id)
    if models is None:
        await _load_models_directory(session, man_id)
        models = _models_cache.get(man_id, {})

    return models.get(model_id, "")


async def _load_models_directory(session: Any, man_id: int) -> list[dict[str, Any]]:
    """Загружает и кеширует справочник моделей для производителя."""
    if not man_id:
        return []

    cached = _models_directory_cache.get(man_id)
    if cached is not None:
        return cached

    directory: list[dict[str, Any]] = []
    lookup: dict[int, str] = {}
    try:
        r = await session.get(
            f"{settings.myauto_api_url}/vehicle/models",
            params={"vehicle_types": "0.1.2", "man_id": man_id},
            headers={"Accept": "application/json"},
        )
        if r.status_code == 200:
            for model in r.json():
                title = str(model.get("title") or "").strip()
                if not title:
                    continue
                entry = {
                    "model_id": int(model["model_id"]),
                    "man_id": int(model.get("man_id") or man_id),
                    "title": title,
                    "group_title": model.get("group_title"),
                }
                directory.append(entry)
                lookup[entry["model_id"]] = title
    except Exception:
        pass

    _models_directory_cache[man_id] = directory
    _models_cache[man_id] = lookup
    return directory


async def _select_model_name(session: Any, man_id: int, model_id: int, raw_model_name: Any) -> str:
    """Выбирает каноничное имя модели: сначала из справочника myauto, затем из объявления."""
    directory_model_name = await _resolve_model_name(session, man_id, model_id)
    if directory_model_name:
        return directory_model_name

    return str(raw_model_name or "").strip()


def _build_image_urls(raw: dict[str, Any]) -> list[str]:
    """Строит список URL фотографий объявления из photo/pic_number/photo_ver."""
    photo_path = str(raw.get("photo") or "").strip()
    car_id = int(raw.get("car_id", 0) or 0)
    pic_number = int(raw.get("pic_number", 0) or 0)
    photo_ver = int(raw.get("photo_ver", 0) or 0)

    if not photo_path or not car_id or pic_number <= 0:
        return []

    version_query = f"?v={photo_ver}" if photo_ver else ""
    return [
        f"{_MYAUTO_IMAGE_BASE_URL}/{photo_path}/large/{car_id}_{index}.jpg{version_query}"
        for index in range(1, pic_number + 1)
    ]


def is_suv_or_crossover_category(category_id: int | None) -> bool:
    return category_id in _SUV_CATEGORY_IDS


async def search_cars(
    make_id: int | None = None,
    model_id: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    price_usd_to: int | None = None,
    page: int = 1,
) -> list[dict[str, Any]]:
    """Возвращает сырые данные с myauto.ge."""
    params: dict[str, Any] = {"Page": page, "SortOrder": 1}
    if make_id:
        params["Mans"] = f"{make_id}.{model_id or 0}"
    if year_from:
        params["YearFrom"] = year_from
    if year_to:
        params["YearTo"] = year_to
    if price_usd_to:
        params["PriceTo"] = price_usd_to
    params["CurrencyID"] = 3  # USD

    try:
        async with _curl_requests.AsyncSession(impersonate=_IMPERSONATE, timeout=15) as client:
            resp = await client.get(
                f"{settings.myauto_api_url}/products",
                params=params,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            items = resp.json().get("data", {}).get("items", [])
            for item in items:
                man_id = int(item.get("man_id", 0))
                model_id = int(item.get("model_id", 0) or 0)
                item["man_name"] = await _resolve_man_name(client, man_id)
                model_name = await _select_model_name(client, man_id, model_id, item.get("car_model"))
                item["model_name"] = model_name
                item["km"] = item.get("car_run_km")
            return items
    except Exception:
        return []


def parse_car(raw: dict[str, Any]) -> CarListing:
    engine_cc = int(raw.get("engine_volume", 0) or 0)
    category_id = int(raw.get("category_id", 0) or 0) or None
    image_urls = _build_image_urls(raw)
    raw_hp = int(raw.get("hp", 0) or 0)
    resolved_spec = resolve_vehicle_spec(raw)
    horse_power = raw_hp if raw_hp > 0 else (resolved_spec.horse_power if resolved_spec else None)
    horse_power_source = "listing_hp" if raw_hp > 0 else (resolved_spec.source if resolved_spec else None)
    fuel_type = _resolve_fuel_type(raw)
    powertrain_kind = _resolve_powertrain_kind(raw, resolved_spec.powertrain_kind if resolved_spec else None)
    util_coefficient = resolved_spec.util_coefficient if resolved_spec else None
    prod_year = int(raw.get("prod_year", 0) or 0)

    if horse_power and engine_cc and prod_year:
        try:
            age_years = max(0, date.today().year - prod_year)
            util_coefficient, _, _, _ = resolveUtilCoefficient2026PersonalM1(
                powertrain_kind=powertrain_kind or "ICE",
                age_years=age_years,
                power_kw=horse_power * 0.73549875,
                engine_cc=engine_cc,
            )
        except ValueError:
            pass

    return CarListing(
        car_id=raw.get("car_id", 0),
        category_id=category_id,
        make=raw.get("man_name", ""),
        model_id=int(raw.get("model_id", 0) or 0) or None,
        car_model=str(raw.get("car_model") or "").strip() or None,
        model=raw.get("model_name", ""),
        year=raw.get("prod_year", 0),
        price_usd=float(raw.get("price", 0) or 0),
        engine_volume_cc=engine_cc,
        horse_power=horse_power,
        horse_power_source=horse_power_source,
        fuel_type=fuel_type,
        util_coefficient=util_coefficient,
        powertrain_kind=powertrain_kind,
        mileage_km=raw.get("km", None),
        image_url=image_urls[0] if image_urls else None,
        image_urls=image_urls,
        url=f"https://www.myauto.ge/en/pr/{raw.get('car_id', '')}",
    )


async def get_car_by_id(car_id: int) -> dict[str, Any] | None:
    """Получить данные одного автомобиля по car_id."""
    try:
        async with _curl_requests.AsyncSession(impersonate=_IMPERSONATE, timeout=15) as client:
            resp = await client.get(
                f"{settings.myauto_api_url}/products/{car_id}",
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            info = resp.json().get("data", {}).get("info")
            if not info:
                return None
            # Resolve manufacturer name (single-car endpoint has man_id, not man_name)
            man_id = int(info.get("man_id", 0))
            model_id = int(info.get("model_id", 0) or 0)
            man_name = await _resolve_man_name(client, man_id)
            model_name = await _select_model_name(client, man_id, model_id, info.get("car_model"))
            # Normalise to the same field names parse_car() expects
            info["man_name"] = man_name
            info["model_name"] = model_name
            info["km"] = info.get("car_run_km")
            return info
    except Exception:
        return None


async def get_makes() -> list[dict[str, Any]]:
    """Список марок с myauto.ge."""
    try:
        async with _curl_requests.AsyncSession(impersonate=_IMPERSONATE, timeout=10) as client:
            resp = await client.get(f"{settings.myauto_api_url}/makes")
            resp.raise_for_status()
            return resp.json().get("data", [])
    except Exception:
        return []


async def get_models(make_id: int) -> list[dict[str, Any]]:
    """Список моделей для марки с myauto.ge."""
    try:
        async with _curl_requests.AsyncSession(impersonate=_IMPERSONATE, timeout=10) as client:
            return await _load_models_directory(client, make_id)
    except Exception:
        return []
