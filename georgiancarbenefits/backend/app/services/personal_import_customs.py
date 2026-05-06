from __future__ import annotations

from typing import Literal, TypedDict


PowertrainKind = Literal["ICE", "OTHER_HYBRID", "EV", "SERIES_HYBRID"]
AgeCategory = Literal["LE_3", "BETWEEN_3_AND_5", "GT_5"]

PASSENGER_CAR_UTIL_BASE_RATE_RUB = 20_000
HP_TO_KW = 0.73549875


class PersonalImportInput(TypedDict):
    price: float
    currencyToRubRate: float
    eurToRubRate: float
    engineCc: int
    horsePower: float
    ageYears: float
    isPersonalUse: bool
    powertrainKind: PowertrainKind | None


class OutputDetails(TypedDict):
    ageCategory: AgeCategory
    customsFeeMethod: str
    unifiedRateMethod: str
    utilFeeMethod: str
    powerKwUsed: float
    powertrainKind: PowertrainKind
    utilMatchedEngineRangeCc: str | None
    utilMatchedPowerRangeKw: str


class PersonalImportOutput(TypedDict):
    customsValueRub: float
    customsValueEur: float
    customsFee: float
    unifiedRate: float
    utilCoefficient: float
    utilFee: float
    total: float
    details: OutputDetails


class CoeffPair(TypedDict):
    newVehicle: float
    usedVehicle: float


class PowerBand(TypedDict):
    maxKw: float
    label: str
    coeff: CoeffPair


class EngineBand(TypedDict):
    maxEngineCc: float
    label: str
    powerBands: list[PowerBand]


EV_OR_SERIES_HYBRID_2026: list[PowerBand] = [
    {"maxKw": 58.84, "label": "≤ 58.84 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
    {"maxKw": 73.55, "label": "58.85–73.55 kW", "coeff": {"newVehicle": 49.56, "usedVehicle": 82.08}},
    {"maxKw": 95.61, "label": "73.56–95.61 kW", "coeff": {"newVehicle": 65.88, "usedVehicle": 95.64}},
    {"maxKw": 117.68, "label": "95.62–117.68 kW", "coeff": {"newVehicle": 78, "usedVehicle": 111.36}},
    {"maxKw": 139.75, "label": "117.69–139.75 kW", "coeff": {"newVehicle": 92.4, "usedVehicle": 129.72}},
    {"maxKw": 161.81, "label": "139.76–161.81 kW", "coeff": {"newVehicle": 109.68, "usedVehicle": 151.2}},
    {"maxKw": 183.88, "label": "161.82–183.88 kW", "coeff": {"newVehicle": 129.96, "usedVehicle": 176.16}},
    {"maxKw": 205.94, "label": "183.89–205.94 kW", "coeff": {"newVehicle": 153.96, "usedVehicle": 205.2}},
    {"maxKw": 228.0, "label": "205.95–228.00 kW", "coeff": {"newVehicle": 182.4, "usedVehicle": 239.04}},
    {"maxKw": 250.07, "label": "228.01–250.07 kW", "coeff": {"newVehicle": 182.4, "usedVehicle": 239.04}},
    {"maxKw": 272.13, "label": "250.08–272.13 kW", "coeff": {"newVehicle": 182.4, "usedVehicle": 239.04}},
    {"maxKw": 294.2, "label": "272.14–294.20 kW", "coeff": {"newVehicle": 182.4, "usedVehicle": 239.04}},
    {"maxKw": 316.26, "label": "294.21–316.26 kW", "coeff": {"newVehicle": 182.4, "usedVehicle": 239.04}},
    {"maxKw": 338.33, "label": "316.27–338.33 kW", "coeff": {"newVehicle": 182.4, "usedVehicle": 239.04}},
    {"maxKw": 367.75, "label": "338.34–367.75 kW", "coeff": {"newVehicle": 182.4, "usedVehicle": 239.04}},
    {"maxKw": float("inf"), "label": "≥ 367.76 kW", "coeff": {"newVehicle": 182.4, "usedVehicle": 239.04}},
]

ICE_OR_OTHER_HYBRID_2026: list[EngineBand] = [
    {
        "maxEngineCc": 1000,
        "label": "≤ 1000 cc",
        "powerBands": [
            {"maxKw": 51.48, "label": "≤ 51.48 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 73.55, "label": "51.49–73.55 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 95.61, "label": "73.56–95.61 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 117.68, "label": "95.62–117.68 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 139.75, "label": "117.69–139.75 kW", "coeff": {"newVehicle": 15.36, "usedVehicle": 28.44}},
            {"maxKw": 161.81, "label": "139.76–161.81 kW", "coeff": {"newVehicle": 15.84, "usedVehicle": 29.28}},
            {"maxKw": 183.88, "label": "161.82–183.88 kW", "coeff": {"newVehicle": 16.2, "usedVehicle": 30.12}},
            {"maxKw": 205.94, "label": "183.89–205.94 kW", "coeff": {"newVehicle": 17.28, "usedVehicle": 30.12}},
            {"maxKw": 228.0, "label": "205.95–228.00 kW", "coeff": {"newVehicle": 17.28, "usedVehicle": 30.12}},
            {"maxKw": 250.07, "label": "228.01–250.07 kW", "coeff": {"newVehicle": 17.28, "usedVehicle": 30.12}},
            {"maxKw": 272.13, "label": "250.08–272.13 kW", "coeff": {"newVehicle": 17.28, "usedVehicle": 30.12}},
            {"maxKw": 294.2, "label": "272.14–294.20 kW", "coeff": {"newVehicle": 17.28, "usedVehicle": 30.12}},
            {"maxKw": 316.26, "label": "294.21–316.26 kW", "coeff": {"newVehicle": 17.28, "usedVehicle": 30.12}},
            {"maxKw": 338.33, "label": "316.27–338.33 kW", "coeff": {"newVehicle": 17.28, "usedVehicle": 30.12}},
            {"maxKw": 367.75, "label": "338.34–367.75 kW", "coeff": {"newVehicle": 17.28, "usedVehicle": 30.12}},
            {"maxKw": float("inf"), "label": "≥ 367.76 kW", "coeff": {"newVehicle": 17.28, "usedVehicle": 30.12}},
        ],
    },
    {
        "maxEngineCc": 2000,
        "label": "1001–2000 cc",
        "powerBands": [
            {"maxKw": 51.48, "label": "≤ 51.48 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 73.55, "label": "51.49–73.55 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 95.61, "label": "73.56–95.61 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 117.68, "label": "95.62–117.68 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 139.75, "label": "117.69–139.75 kW", "coeff": {"newVehicle": 45, "usedVehicle": 74.64}},
            {"maxKw": 161.81, "label": "139.76–161.81 kW", "coeff": {"newVehicle": 47.64, "usedVehicle": 79.2}},
            {"maxKw": 183.88, "label": "161.82–183.88 kW", "coeff": {"newVehicle": 50.52, "usedVehicle": 83.88}},
            {"maxKw": 205.94, "label": "183.89–205.94 kW", "coeff": {"newVehicle": 57.12, "usedVehicle": 91.92}},
            {"maxKw": 228.0, "label": "205.95–228.00 kW", "coeff": {"newVehicle": 64.56, "usedVehicle": 100.56}},
            {"maxKw": 250.07, "label": "228.01–250.07 kW", "coeff": {"newVehicle": 72.96, "usedVehicle": 110.16}},
            {"maxKw": 272.13, "label": "250.08–272.13 kW", "coeff": {"newVehicle": 83.16, "usedVehicle": 120.6}},
            {"maxKw": 294.2, "label": "272.14–294.20 kW", "coeff": {"newVehicle": 94.8, "usedVehicle": 132}},
            {"maxKw": 316.26, "label": "294.21–316.26 kW", "coeff": {"newVehicle": 108, "usedVehicle": 144.6}},
            {"maxKw": 338.33, "label": "316.27–338.33 kW", "coeff": {"newVehicle": 123.24, "usedVehicle": 158.4}},
            {"maxKw": 367.75, "label": "338.34–367.75 kW", "coeff": {"newVehicle": 140.4, "usedVehicle": 173.4}},
            {"maxKw": float("inf"), "label": "≥ 367.76 kW", "coeff": {"newVehicle": 160.08, "usedVehicle": 189.84}},
        ],
    },
    {
        "maxEngineCc": 3000,
        "label": "2001–3000 cc",
        "powerBands": [
            {"maxKw": 51.48, "label": "≤ 51.48 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 73.55, "label": "51.49–73.55 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 95.61, "label": "73.56–95.61 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 117.68, "label": "95.62–117.68 kW", "coeff": {"newVehicle": 0.17, "usedVehicle": 0.26}},
            {"maxKw": 139.75, "label": "117.69–139.75 kW", "coeff": {"newVehicle": 115.34, "usedVehicle": 172.8}},
            {"maxKw": 161.81, "label": "139.76–161.81 kW", "coeff": {"newVehicle": 118.2, "usedVehicle": 175.08}},
            {"maxKw": 183.88, "label": "161.82–183.88 kW", "coeff": {"newVehicle": 120.12, "usedVehicle": 177.6}},
            {"maxKw": 205.94, "label": "183.89–205.94 kW", "coeff": {"newVehicle": 126, "usedVehicle": 183}},
            {"maxKw": 228.0, "label": "205.95–228.00 kW", "coeff": {"newVehicle": 131.04, "usedVehicle": 188.52}},
            {"maxKw": 250.07, "label": "228.01–250.07 kW", "coeff": {"newVehicle": 136.32, "usedVehicle": 193.68}},
            {"maxKw": 272.13, "label": "250.08–272.13 kW", "coeff": {"newVehicle": 141.72, "usedVehicle": 199.08}},
            {"maxKw": 294.2, "label": "272.14–294.20 kW", "coeff": {"newVehicle": 147.48, "usedVehicle": 204.72}},
            {"maxKw": 316.26, "label": "294.21–316.26 kW", "coeff": {"newVehicle": 153.36, "usedVehicle": 210.48}},
            {"maxKw": 338.33, "label": "316.27–338.33 kW", "coeff": {"newVehicle": 159.48, "usedVehicle": 216.36}},
            {"maxKw": 367.75, "label": "338.34–367.75 kW", "coeff": {"newVehicle": 165.84, "usedVehicle": 222.36}},
            {"maxKw": float("inf"), "label": "≥ 367.76 kW", "coeff": {"newVehicle": 172.44, "usedVehicle": 228.6}},
        ],
    },
    {
        "maxEngineCc": 3500,
        "label": "3001–3500 cc",
        "powerBands": [
            {"maxKw": 51.48, "label": "≤ 51.48 kW", "coeff": {"newVehicle": 189.17, "usedVehicle": 289.61}},
            {"maxKw": 73.55, "label": "51.49–73.55 kW", "coeff": {"newVehicle": 189.17, "usedVehicle": 289.61}},
            {"maxKw": 95.61, "label": "73.56–95.61 kW", "coeff": {"newVehicle": 189.17, "usedVehicle": 289.61}},
            {"maxKw": 117.68, "label": "95.62–117.68 kW", "coeff": {"newVehicle": 189.17, "usedVehicle": 289.61}},
            {"maxKw": 139.75, "label": "117.69–139.75 kW", "coeff": {"newVehicle": 131.76, "usedVehicle": 200.04}},
            {"maxKw": 161.81, "label": "139.76–161.81 kW", "coeff": {"newVehicle": 134.4, "usedVehicle": 202.2}},
            {"maxKw": 183.88, "label": "161.82–183.88 kW", "coeff": {"newVehicle": 137.16, "usedVehicle": 204.36}},
            {"maxKw": 205.94, "label": "183.89–205.94 kW", "coeff": {"newVehicle": 140.52, "usedVehicle": 207.24}},
            {"maxKw": 228.0, "label": "205.95–228.00 kW", "coeff": {"newVehicle": 144, "usedVehicle": 212.4}},
            {"maxKw": 250.07, "label": "228.01–250.07 kW", "coeff": {"newVehicle": 151.92, "usedVehicle": 217.8}},
            {"maxKw": 272.13, "label": "250.08–272.13 kW", "coeff": {"newVehicle": 160.32, "usedVehicle": 224.28}},
            {"maxKw": 294.2, "label": "272.14–294.20 kW", "coeff": {"newVehicle": 169.2, "usedVehicle": 231}},
            {"maxKw": 316.26, "label": "294.21–316.26 kW", "coeff": {"newVehicle": 178.44, "usedVehicle": 237.96}},
            {"maxKw": 338.33, "label": "316.27–338.33 kW", "coeff": {"newVehicle": 188.28, "usedVehicle": 245.04}},
            {"maxKw": 367.75, "label": "338.34–367.75 kW", "coeff": {"newVehicle": 198.6, "usedVehicle": 252.48}},
            {"maxKw": float("inf"), "label": "≥ 367.76 kW", "coeff": {"newVehicle": 209.52, "usedVehicle": 260.04}},
        ],
    },
    {
        "maxEngineCc": float("inf"),
        "label": "> 3500 cc",
        "powerBands": [
            {"maxKw": 51.48, "label": "≤ 51.48 kW", "coeff": {"newVehicle": 240.89, "usedVehicle": 316.67}},
            {"maxKw": 73.55, "label": "51.49–73.55 kW", "coeff": {"newVehicle": 240.89, "usedVehicle": 316.67}},
            {"maxKw": 95.61, "label": "73.56–95.61 kW", "coeff": {"newVehicle": 240.89, "usedVehicle": 316.67}},
            {"maxKw": 117.68, "label": "95.62–117.68 kW", "coeff": {"newVehicle": 240.89, "usedVehicle": 316.67}},
            {"maxKw": 139.75, "label": "117.69–139.75 kW", "coeff": {"newVehicle": 167.28, "usedVehicle": 219.48}},
            {"maxKw": 161.81, "label": "139.76–161.81 kW", "coeff": {"newVehicle": 170.16, "usedVehicle": 222.84}},
            {"maxKw": 183.88, "label": "161.82–183.88 kW", "coeff": {"newVehicle": 173.04, "usedVehicle": 226.2}},
            {"maxKw": 205.94, "label": "183.89–205.94 kW", "coeff": {"newVehicle": 176.52, "usedVehicle": 231.36}},
            {"maxKw": 228.0, "label": "205.95–228.00 kW", "coeff": {"newVehicle": 180, "usedVehicle": 236.64}},
            {"maxKw": 250.07, "label": "228.01–250.07 kW", "coeff": {"newVehicle": 186.36, "usedVehicle": 249.6}},
            {"maxKw": 272.13, "label": "250.08–272.13 kW", "coeff": {"newVehicle": 192.88, "usedVehicle": 263.4}},
            {"maxKw": 294.2, "label": "272.14–294.20 kW", "coeff": {"newVehicle": 199.68, "usedVehicle": 277.92}},
            {"maxKw": 316.26, "label": "294.21–316.26 kW", "coeff": {"newVehicle": 206.64, "usedVehicle": 293.16}},
            {"maxKw": 338.33, "label": "316.27–338.33 kW", "coeff": {"newVehicle": 213.84, "usedVehicle": 309.36}},
            {"maxKw": 367.75, "label": "338.34–367.75 kW", "coeff": {"newVehicle": 221.28, "usedVehicle": 326.4}},
            {"maxKw": float("inf"), "label": "≥ 367.76 kW", "coeff": {"newVehicle": 229.08, "usedVehicle": 344.28}},
        ],
    },
]


def round2(value: float) -> float:
    return round((float(value) + float.fromhex("0x1p-52")) * 100) / 100


def _assert_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be a positive finite number")


def _assert_non_negative(name: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{name} must be a finite number >= 0")


def horsePowerToKw(horse_power: float) -> float:
    _assert_positive("horsePower", horse_power)
    return round2(horse_power * HP_TO_KW)


def getAgeCategory(age_years: float) -> AgeCategory:
    _assert_non_negative("ageYears", age_years)

    if age_years <= 3:
        return "LE_3"
    if age_years <= 5:
        return "BETWEEN_3_AND_5"
    return "GT_5"


def _get_age_key_for_util(age_years: float) -> Literal["newVehicle", "usedVehicle"]:
    return "newVehicle" if age_years <= 3 else "usedVehicle"


def determineCustomsFee2026(customs_value_rub: float) -> tuple[float, str]:
    _assert_positive("customsValueRub", customs_value_rub)

    if customs_value_rub <= 200_000:
        return 1231, "≤ 200000 RUB => 1231 RUB"
    if customs_value_rub <= 450_000:
        return 2462, "200000.01–450000 RUB => 2462 RUB"
    if customs_value_rub <= 1_200_000:
        return 4924, "450000.01–1200000 RUB => 4924 RUB"
    if customs_value_rub <= 2_700_000:
        return 13_541, "1200000.01–2700000 RUB => 13541 RUB"
    if customs_value_rub <= 4_200_000:
        return 18_465, "2700000.01–4200000 RUB => 18465 RUB"
    if customs_value_rub <= 5_500_000:
        return 21_344, "4200000.01–5500000 RUB => 21344 RUB"
    if customs_value_rub <= 10_000_000:
        return 49_240, "5500000.01–10000000 RUB => 49240 RUB"
    return 73_860, "> 10000000 RUB => 73860 RUB"


def determineUnifiedRate(
    *,
    customs_value_rub: float,
    customs_value_eur: float,
    engine_cc: int,
    eur_to_rub_rate: float,
    age_category: AgeCategory,
) -> tuple[float, str]:
    _assert_positive("customsValueRub", customs_value_rub)
    _assert_positive("customsValueEur", customs_value_eur)
    _assert_non_negative("engineCc", float(engine_cc))
    _assert_positive("eurToRubRate", eur_to_rub_rate)

    if age_category == "LE_3":
        if customs_value_eur <= 8500:
            percent_rate = 0.54
            euro_per_cc = 2.5
            range_label = "≤ 8500 EUR => 54% but not less than 2.5 EUR/cc"
        elif customs_value_eur <= 16_700:
            percent_rate = 0.48
            euro_per_cc = 3.5
            range_label = "8500.01–16700 EUR => 48% but not less than 3.5 EUR/cc"
        elif customs_value_eur <= 42_300:
            percent_rate = 0.48
            euro_per_cc = 5.5
            range_label = "16700.01–42300 EUR => 48% but not less than 5.5 EUR/cc"
        elif customs_value_eur <= 84_500:
            percent_rate = 0.48
            euro_per_cc = 7.5
            range_label = "42300.01–84500 EUR => 48% but not less than 7.5 EUR/cc"
        elif customs_value_eur <= 169_000:
            percent_rate = 0.48
            euro_per_cc = 15
            range_label = "84500.01–169000 EUR => 48% but not less than 15 EUR/cc"
        else:
            percent_rate = 0.48
            euro_per_cc = 20
            range_label = "> 169000 EUR => 48% but not less than 20 EUR/cc"

        percent_part = customs_value_rub * percent_rate
        volume_part = engine_cc * euro_per_cc * eur_to_rub_rate
        unified_rate = max(percent_part, volume_part)
        return round2(unified_rate), f"{range_label}; max({round2(percent_part)}, {round2(volume_part)})"

    if age_category == "BETWEEN_3_AND_5":
        if engine_cc <= 1000:
            euro_per_cc = 1.5
        elif engine_cc <= 1500:
            euro_per_cc = 1.7
        elif engine_cc <= 1800:
            euro_per_cc = 2.5
        elif engine_cc <= 2300:
            euro_per_cc = 2.7
        elif engine_cc <= 3000:
            euro_per_cc = 3.0
        else:
            euro_per_cc = 3.6
        return round2(engine_cc * euro_per_cc * eur_to_rub_rate), f"3–5 years => {euro_per_cc} EUR/cc"

    if engine_cc <= 1000:
        euro_per_cc = 3.0
    elif engine_cc <= 1500:
        euro_per_cc = 3.2
    elif engine_cc <= 1800:
        euro_per_cc = 3.5
    elif engine_cc <= 2300:
        euro_per_cc = 4.8
    elif engine_cc <= 3000:
        euro_per_cc = 5.0
    else:
        euro_per_cc = 5.7
    return round2(engine_cc * euro_per_cc * eur_to_rub_rate), f"> 5 years => {euro_per_cc} EUR/cc"


def _find_power_band(power_bands: list[PowerBand], power_kw: float) -> PowerBand:
    for band in power_bands:
        if power_kw <= band["maxKw"]:
            return band
    raise ValueError(f"No power band found for powerKw={power_kw}")


def _find_engine_band(engine_bands: list[EngineBand], engine_cc: int) -> EngineBand:
    for band in engine_bands:
        if engine_cc <= band["maxEngineCc"]:
            return band
    raise ValueError(f"No engine band found for engineCc={engine_cc}")


def resolveUtilCoefficient2026PersonalM1(
    *,
    powertrain_kind: PowertrainKind,
    age_years: float,
    power_kw: float,
    engine_cc: int,
) -> tuple[float, str, str | None, str]:
    _assert_non_negative("ageYears", age_years)
    _assert_positive("powerKw", power_kw)

    age_key = _get_age_key_for_util(age_years)

    if powertrain_kind in ("EV", "SERIES_HYBRID"):
        power_band = _find_power_band(EV_OR_SERIES_HYBRID_2026, power_kw)
        coefficient = round2(power_band["coeff"][age_key])
        return (
            coefficient,
            f"2026 personal-use M1 {powertrain_kind} => {power_band['label']}",
            None,
            power_band["label"],
        )

    _assert_positive("engineCc", float(engine_cc))

    engine_band = _find_engine_band(ICE_OR_OTHER_HYBRID_2026, engine_cc)
    power_band = _find_power_band(engine_band["powerBands"], power_kw)
    coefficient = round2(power_band["coeff"][age_key])
    return (
        coefficient,
        f"2026 personal-use M1 {powertrain_kind} => {engine_band['label']}, {power_band['label']}",
        engine_band["label"],
        power_band["label"],
    )


def calculatePersonalImportCustoms(input: PersonalImportInput) -> PersonalImportOutput:
    powertrain_kind = input.get("powertrainKind") or "ICE"

    _assert_positive("price", float(input["price"]))
    _assert_positive("currencyToRubRate", float(input["currencyToRubRate"]))
    _assert_positive("eurToRubRate", float(input["eurToRubRate"]))
    _assert_positive("horsePower", float(input["horsePower"]))
    _assert_non_negative("ageYears", float(input["ageYears"]))

    engine_cc = int(input["engineCc"])
    if powertrain_kind in ("EV", "SERIES_HYBRID"):
        _assert_non_negative("engineCc", float(engine_cc))
    else:
        _assert_positive("engineCc", float(engine_cc))

    if input["isPersonalUse"] is not True:
        raise ValueError(
            "This calculator supports only personal import by an individual (isPersonalUse must be true)"
        )

    customs_value_rub = round2(float(input["price"]) * float(input["currencyToRubRate"]))
    customs_value_eur = round2(customs_value_rub / float(input["eurToRubRate"]))
    age_category = getAgeCategory(float(input["ageYears"]))
    power_kw_used = horsePowerToKw(float(input["horsePower"]))

    customs_fee, customs_fee_method = determineCustomsFee2026(customs_value_rub)
    unified_rate, unified_rate_method = determineUnifiedRate(
        customs_value_rub=customs_value_rub,
        customs_value_eur=customs_value_eur,
        engine_cc=engine_cc,
        eur_to_rub_rate=float(input["eurToRubRate"]),
        age_category=age_category,
    )
    util_coefficient, util_fee_method, matched_engine_range_cc, matched_power_range_kw = resolveUtilCoefficient2026PersonalM1(
        powertrain_kind=powertrain_kind,
        age_years=float(input["ageYears"]),
        power_kw=power_kw_used,
        engine_cc=engine_cc,
    )
    util_fee = round2(PASSENGER_CAR_UTIL_BASE_RATE_RUB * util_coefficient)
    total = round2(customs_fee + unified_rate + util_fee)

    return {
        "customsValueRub": customs_value_rub,
        "customsValueEur": customs_value_eur,
        "customsFee": round2(customs_fee),
        "unifiedRate": round2(unified_rate),
        "utilCoefficient": util_coefficient,
        "utilFee": util_fee,
        "total": total,
        "details": {
            "ageCategory": age_category,
            "customsFeeMethod": customs_fee_method,
            "unifiedRateMethod": unified_rate_method,
            "utilFeeMethod": util_fee_method,
            "powerKwUsed": power_kw_used,
            "powertrainKind": powertrain_kind,
            "utilMatchedEngineRangeCc": matched_engine_range_cc,
            "utilMatchedPowerRangeKw": matched_power_range_kw,
        },
    }


if __name__ == "__main__":
    print(
        calculatePersonalImportCustoms(
            {
                "price": 148000,
                "currencyToRubRate": 78.7496,
                "eurToRubRate": 91.0279,
                "engineCc": 3500,
                "horsePower": 415,
                "ageYears": 1,
                "isPersonalUse": True,
                "powertrainKind": "ICE",
            }
        )
    )