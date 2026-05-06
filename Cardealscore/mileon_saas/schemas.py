from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CompanyCreate(BaseModel):
    name: str
    plan: Optional[str] = None


class CompanyRead(BaseModel):
    id: int
    name: str
    plan: Optional[str] = None
    roi_thresholds: Optional[dict] = None
    brand_whitelist: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    company_id: int
    role: str


class UserRead(BaseModel):
    id: int
    company_id: int
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CarListingCreate(BaseModel):
    company_id: int
    brand: str
    model: str
    year: Optional[int] = None
    engine_type: Optional[str] = None
    engine_code: Optional[str] = None
    engine_volume: Optional[int] = None
    transmission: Optional[str] = None
    transmission_code: Optional[str] = None
    drivetrain: Optional[str] = None
    mileage_km: Optional[int] = None
    price_usd: Optional[float] = None
    owners_count: Optional[int] = None
    accident_history: Optional[str] = None
    imported_from: Optional[str] = None
    vin: Optional[str] = None
    source: Optional[str] = "myauto"
    source_listing_id: Optional[str] = None


class CarListingRead(BaseModel):
    id: int
    company_id: int
    brand: str
    model: str
    year: Optional[int] = None
    engine_type: Optional[str] = None
    engine_code: Optional[str] = None
    engine_volume: Optional[int] = None
    transmission: Optional[str] = None
    transmission_code: Optional[str] = None
    drivetrain: Optional[str] = None
    mileage_km: Optional[int] = None
    price_usd: Optional[float] = None
    owners_count: Optional[int] = None
    accident_history: Optional[str] = None
    imported_from: Optional[str] = None
    vin: Optional[str] = None
    source: Optional[str] = None
    source_listing_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketStatsRead(BaseModel):
    id: int
    company_id: int
    brand: str
    model: str
    year: Optional[int] = None
    engine_type: Optional[str] = None
    transmission: Optional[str] = None
    drivetrain: Optional[str] = None
    median_price_usd: Optional[float] = None
    q1_price_usd: Optional[float] = None
    q3_price_usd: Optional[float] = None
    avg_mileage_km: Optional[float] = None
    listings_count: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrandPolicyCreate(BaseModel):
    company_id: int
    brand: str
    enabled: bool = True
    liquidity_multiplier: float = 1.0
    max_hold_days: int = 60
    min_roi_required: float = 12.0


class BrandPolicyRead(BaseModel):
    id: int
    company_id: int
    brand: str
    enabled: bool
    liquidity_multiplier: float
    max_hold_days: int
    min_roi_required: float

    model_config = ConfigDict(from_attributes=True)


class TechnicalBlacklistCreate(BaseModel):
    company_id: int
    brand: str
    component_type: str
    component_code: str
    reason: Optional[str] = None
    severity: str = "medium"


class TechnicalBlacklistRead(BaseModel):
    id: int
    company_id: int
    brand: str
    component_type: str
    component_code: str
    reason: Optional[str] = None
    severity: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListingScores(BaseModel):
    deal_score: float
    buy_score: float
    price_score: float
    mileage_score: float
    liquidity_score: float
    condition_score: float
    risk_score: float
    expected_sell_price: float
    ml_expected_price: Optional[float] = None
    net_profit: float
    roi_percent: float
    expected_hold_days: int
    decision: str
    ml_confidence: float
    risk_flags: list[str]
    blacklist_blocked: bool


class ListingWithScores(BaseModel):
    listing: CarListingRead
    scores: Optional[ListingScores] = None
