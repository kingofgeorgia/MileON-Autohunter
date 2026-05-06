from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

from mileon_saas.config import settings


@dataclass
class MLModelBundle:
    model: GradientBoostingRegressor
    columns: list[str]
    r2: float


def build_features(records: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    categorical = [
        "brand",
        "model",
        "engine_type",
        "transmission",
        "drivetrain",
        "imported_from",
        "accident_history",
    ]
    numeric = [
        "year",
        "mileage_km",
        "owners_count",
        "mileage_deviation",
        "price_vs_market",
        "liquidity_score",
        "condition_score",
    ]
    df[categorical] = df[categorical].fillna("unknown")
    df[numeric] = df[numeric].fillna(0)
    return pd.get_dummies(df[categorical + numeric], columns=categorical)


def train_model(training_records: Iterable[Dict[str, Any]], target_field: str = "sell_price") -> MLModelBundle:
    df = pd.DataFrame(training_records)
    if df.empty:
        raise ValueError("No training data provided")

    y = df[target_field]
    X = build_features(training_records)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = GradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    r2 = r2_score(y_test, preds)

    return MLModelBundle(model=model, columns=list(X.columns), r2=r2)


def save_model(bundle: MLModelBundle) -> None:
    Path(settings.ml_model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle.model, settings.ml_model_path)
    metadata = {"columns": bundle.columns, "r2": bundle.r2}
    with open(settings.ml_metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def load_model() -> Optional[MLModelBundle]:
    if not Path(settings.ml_model_path).exists() or not Path(settings.ml_metadata_path).exists():
        return None

    model = joblib.load(settings.ml_model_path)
    with open(settings.ml_metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return MLModelBundle(model=model, columns=metadata.get("columns", []), r2=metadata.get("r2", 0.0))


def predict_price(bundle: MLModelBundle, features: Dict[str, Any]) -> float:
    data = build_features([features])
    for col in bundle.columns:
        if col not in data.columns:
            data[col] = 0
    data = data[bundle.columns]
    return float(bundle.model.predict(data)[0])


def confidence(bundle: Optional[MLModelBundle]) -> float:
    if not bundle:
        return 0.0
    return max(0.0, min(1.0, bundle.r2))
