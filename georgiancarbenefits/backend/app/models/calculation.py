from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Calculation(Base):
    __tablename__ = "calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Input
    car_price_usd: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    engine_volume_cc: Mapped[int] = mapped_column(Integer, nullable=False)
    car_year: Mapped[int] = mapped_column(Integer, nullable=False)
    horse_power: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    util_coefficient: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    powertrain_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    power_kw_override: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_personal_use: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    logistics_cost_rub: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    rf_analog_price_rub: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Snapshot of calculated values
    customs_duty_rub: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    recycling_fee_rub: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    total_cost_rub: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    usd_to_rub: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    eur_to_rub: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    gel_to_rub: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="calculations")
