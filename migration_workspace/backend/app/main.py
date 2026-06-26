from fastapi import FastAPI
from pydantic import BaseModel, Field

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from shared.calculator import EstimateRequest, estimate_import_cost, parse_myauto_url

app = FastAPI(title="MileON Autohunter Backend", version="0.1.0")


class EstimatePayload(BaseModel):
    car_price: float = Field(..., gt=0)
    engine_volume: float = Field(2.0, gt=0)
    engine_power: int = Field(180, gt=0)
    year: int = Field(2018, gt=1900)
    fuel_type: str = "petrol"
    customs_rate: float = Field(0.4, ge=0.1, le=0.8)
    logistics_cost: float = Field(0.0, ge=0)
    broker_fee: float = Field(0.0, ge=0)
    registration_cost: float = Field(0.0, ge=0)
    currency: str = "RUB"
    source_url: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "backend"}


@app.post("/api/calculator/estimate")
def estimate(payload: EstimatePayload) -> dict:
    request = EstimateRequest(**payload.model_dump())
    result = estimate_import_cost(request)
    return {"status": "ok", "result": result}


@app.post("/api/calculator/parse-myauto")
def parse_myauto(payload: dict) -> dict:
    url = payload.get("url")
    return {"status": "ok", "result": parse_myauto_url(url)}
