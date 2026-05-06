from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from app.services.personal_import_customs import PowertrainKind


@dataclass(frozen=True)
class VehicleSpecEntry:
    make: str
    model: str
    year_from: int
    year_to: int
    horse_power: int
    make_aliases: tuple[str, ...] = ()
    model_aliases: tuple[str, ...] = ()
    man_id: int | None = None
    model_id: int | None = None
    engine_cc: int | None = None
    fuel_type_id: int | None = None
    util_coefficient: float | None = None
    powertrain_kind: PowertrainKind | None = None


@dataclass(frozen=True)
class ResolvedVehicleSpec:
    horse_power: int
    util_coefficient: float | None
    powertrain_kind: PowertrainKind | None
    source: str


_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "vehicle_specs.json"


def _load_vehicle_specs() -> tuple[VehicleSpecEntry, ...]:
    raw_entries = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    specs: list[VehicleSpecEntry] = []
    for entry in raw_entries:
        specs.append(
            VehicleSpecEntry(
                make=str(entry["make"]),
                model=str(entry["model"]),
                make_aliases=tuple(str(item).lower() for item in entry.get("make_aliases", [])),
                model_aliases=tuple(str(item).lower() for item in entry.get("model_aliases", [])),
                man_id=int(entry["man_id"]) if entry.get("man_id") is not None else None,
                model_id=int(entry["model_id"]) if entry.get("model_id") is not None else None,
                year_from=int(entry["year_from"]),
                year_to=int(entry["year_to"]),
                engine_cc=int(entry["engine_cc"]) if entry.get("engine_cc") is not None else None,
                fuel_type_id=int(entry["fuel_type_id"]) if entry.get("fuel_type_id") is not None else None,
                horse_power=int(entry["horse_power"]),
                util_coefficient=float(entry["util_coefficient"]) if entry.get("util_coefficient") is not None else None,
                powertrain_kind=str(entry["powertrain_kind"]) if entry.get("powertrain_kind") is not None else None,
            )
        )
    return tuple(specs)


_VEHICLE_SPECS = _load_vehicle_specs()


def resolve_vehicle_spec(raw: dict[str, Any]) -> ResolvedVehicleSpec | None:
    man_id = int(raw.get("man_id", 0) or 0)
    model_id = int(raw.get("model_id", 0) or 0)
    prod_year = int(raw.get("prod_year", 0) or 0)
    engine_cc = int(raw.get("engine_volume", 0) or 0)
    fuel_type_id = int(raw.get("fuel_type_id", 0) or 0)

    if not prod_year:
        return None

    make_haystack = " ".join(
        _normalize_text(raw.get(field)) for field in ("man_name", "make")
    ).strip()
    haystack = " ".join(
        _normalize_text(raw.get(field))
        for field in ("model_name", "car_model", "trim_name", "car_desc")
    ).strip()

    best_match: VehicleSpecEntry | None = None
    best_score = -1

    for entry in _VEHICLE_SPECS:
        if not (entry.year_from <= prod_year <= entry.year_to):
            continue

        score = 0

        if entry.man_id is not None and man_id:
            if entry.man_id != man_id:
                continue
            score += 6

        if entry.model_id is not None and model_id:
            if entry.model_id != model_id:
                continue
            score += 6

        if entry.engine_cc is not None and engine_cc:
            if entry.engine_cc != engine_cc:
                continue
            score += 3

        if entry.fuel_type_id is not None and fuel_type_id:
            if entry.fuel_type_id != fuel_type_id:
                continue
            score += 3

        make_tokens = {entry.make.lower(), *entry.make_aliases}
        if make_haystack:
            if not any(token in make_haystack for token in make_tokens):
                if entry.man_id is None:
                    continue
            else:
                score += 4

        model_tokens = {entry.model.lower(), *entry.model_aliases}
        model_hits = sum(1 for alias in model_tokens if alias and alias in haystack)
        if model_hits == 0:
            if entry.model_id is None:
                continue
        else:
            score += model_hits

        if score <= 0:
            continue

        if score > best_score:
            best_match = entry
            best_score = score

    if best_match is None:
        return None

    return ResolvedVehicleSpec(
        horse_power=best_match.horse_power,
        util_coefficient=best_match.util_coefficient,
        powertrain_kind=best_match.powertrain_kind,
        source="spec_catalog",
    )


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())