from datetime import datetime
from typing import Optional


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def expected_mileage(year: Optional[int]) -> Optional[int]:
    if not year:
        return None
    current_year = datetime.utcnow().year
    age = max(current_year - year, 0)
    return age * 15000


def condition_score(accident_history: Optional[str]) -> float:
    mapping = {
        "none": 1.0,
        "cosmetic": 0.7,
        "structural": 0.3,
        "unknown": 0.5,
    }
    if not accident_history:
        return mapping["unknown"]
    return mapping.get(accident_history.lower(), mapping["unknown"])
