"""
Таможенные пошлины РФ для физических лиц (ЕАЭС).
Источник: ТК ЕАЭС, Решение Совета ЕЭК № 107 (актуальные ставки 2024).

Ставки:
  До 3 лет:  max(48% от цены€, X евро/куб.см)
  3–5 лет:   max(48% от цены€, Y евро/куб.см)   (только комбинированная)
  Старше 5:  только адвалорная/специфическая — Y евро/куб.см

Объём двигателя (куб.см) → (до 3 лет, 3-5 лет, старше 5)
"""

from datetime import date

# (eur_per_cc_new, eur_per_cc_3_5, eur_per_cc_5plus)
_RATES: list[tuple[int, float, float, float]] = [
    (1000,  1.5,  2.5, 3.0),
    (1500,  1.7,  2.7, 3.2),
    (1800,  2.5,  3.5, 4.0),
    (2300,  2.7,  3.7, 4.5),
    (3000,  3.0,  4.0, 5.0),
    (999_999, 3.6, 4.8, 5.7),
]


def _rate_per_cc(engine_cc: int, age_years: float) -> float:
    for max_cc, r_new, r_3_5, r_5plus in _RATES:
        if engine_cc <= max_cc:
            if age_years < 3:
                return r_new
            elif age_years <= 5:
                return r_3_5
            else:
                return r_5plus
    return 5.7  # fallback


def calculate_customs_duty(
    price_usd: float,
    engine_cc: int,
    car_year: int,
    usd_to_eur: float,
    eur_to_rub: float,
) -> float:
    """
    Возвращает таможенную пошлину в рублях.
    usd_to_eur — курс 1 USD в EUR.
    """
    age_years = date.today().year - car_year

    price_eur = price_usd * usd_to_eur
    rate = _rate_per_cc(engine_cc, age_years)

    specific_duty_eur = rate * engine_cc
    advalorem_duty_eur = price_eur * 0.48

    if age_years < 3:
        duty_eur = max(advalorem_duty_eur, specific_duty_eur)
    elif age_years <= 5:
        duty_eur = max(advalorem_duty_eur, specific_duty_eur)
    else:
        duty_eur = specific_duty_eur

    return round(duty_eur * eur_to_rub, 2)
