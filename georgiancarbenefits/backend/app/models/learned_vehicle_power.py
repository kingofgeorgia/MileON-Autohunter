from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LearnedVehiclePower(Base):
    __tablename__ = "learned_vehicle_powers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    make: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_make: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    normalized_model: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    model_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    horse_power: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )