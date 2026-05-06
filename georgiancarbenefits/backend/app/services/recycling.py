"""
Утилизационный сбор РФ для физических лиц.
Источник: Постановление Правительства РФ № 1291 (ред. 2024).

Базовая ставка: 20 000 руб.
Коэффициенты зависят от объёма двигателя и возраста авто.
"""

from datetime import date

# (max_cc_exclusive, coeff_under_3_years, coeff_3plus_years)
_COEFFS: list[tuple[int, float, float]] = [
    (1000,  0.17,  0.26),
    (2000,  0.17,  0.26),
    (3000,  0.17,  0.26),
    (3500,  0.17,  0.26),
    (999_999, 0.17, 0.26),
]

BASE_RATE_RUB = 20_000.0


def calculate_recycling_fee(engine_cc: int, car_year: int) -> float:
    """Возвращает утилизационный сбор в рублях."""
    age_years = date.today().year - car_year

    for max_cc, coeff_new, coeff_old in _COEFFS:
        if engine_cc <= max_cc:
            coeff = coeff_new if age_years < 3 else coeff_old
            return round(BASE_RATE_RUB * coeff, 2)

    # fallback — самый крупный коэффициент
    coeff = 0.17 if (date.today().year - car_year) < 3 else 0.26
    return round(BASE_RATE_RUB * coeff, 2)
