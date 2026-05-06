from pydantic import BaseModel, ConfigDict

from app.services.personal_import_customs import PowertrainKind


class CarModelOption(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: int
    man_id: int
    title: str
    group_title: str | None = None


class CarListing(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    car_id: int
    category_id: int | None = None
    make: str
    model_id: int | None = None
    car_model: str | None = None
    model: str
    year: int
    price_usd: float
    engine_volume_cc: int
    horse_power: int | None = None
    horse_power_source: str | None = None
    fuel_type: str | None = None
    util_coefficient: float | None = None
    powertrain_kind: PowertrainKind | None = None
    mileage_km: int | None
    image_url: str | None
    image_urls: list[str] = []
    url: str
    estimated_total_rub: float | None = None
