from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mileon_saas.db import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    roi_thresholds: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    brand_whitelist: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="company")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    role: Mapped[str] = mapped_column(String(20), default="buyer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="users")


class CarListing(Base):
    __tablename__ = "car_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    source: Mapped[str] = mapped_column(String(50), default="myauto")
    source_listing_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Basic info
    brand: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Engine specs
    engine_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    engine_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    engine_volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cylinders: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Transmission
    transmission: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transmission_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Drivetrain
    drivetrain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Body
    doors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Mileage and price
    mileage_km: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # History
    owners_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    accident_history: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    imported_from: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    customs_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # VIN and identification
    vin: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    car_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Source car ID
    
    # Location and status
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dealer_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Photo and description
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    
    # Features and metadata
    features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # ABS, AC, etc.
    listing_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Any extra data
    
    # Timestamps
    listing_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # When posted
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # When added to our DB


class MarketStats(Base):
    __tablename__ = "market_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    brand: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    engine_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transmission: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    drivetrain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    median_price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    q1_price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    q3_price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_mileage_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    listings_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClosedDeal(Base):
    __tablename__ = "closed_deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    listing_id: Mapped[int] = mapped_column(ForeignKey("car_listings.id"))
    purchase_price: Mapped[float] = mapped_column(Float)
    sell_price: Mapped[float] = mapped_column(Float)
    days_held: Mapped[int] = mapped_column(Integer)
    repair_cost: Mapped[float] = mapped_column(Float, default=0.0)
    net_profit: Mapped[float] = mapped_column(Float)
    roi_percent: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BrandPolicy(Base):
    __tablename__ = "brand_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    brand: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    liquidity_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    max_hold_days: Mapped[int] = mapped_column(Integer, default=60)
    min_roi_required: Mapped[float] = mapped_column(Float, default=12.0)


class TechnicalBlacklist(Base):
    __tablename__ = "technical_blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    brand: Mapped[str] = mapped_column(String(100))
    component_type: Mapped[str] = mapped_column(String(20))
    component_code: Mapped[str] = mapped_column(String(50))
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(10), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TelegramSubscription(Base):
    __tablename__ = "telegram_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    role: Mapped[str] = mapped_column(String(20), default="buyer")
    chat_id: Mapped[str] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ListingAction(Base):
    __tablename__ = "listing_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("car_listings.id"))
    chat_id: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
