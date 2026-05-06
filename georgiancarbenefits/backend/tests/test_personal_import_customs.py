from app.services.personal_import_customs import (
    calculatePersonalImportCustoms,
    determineCustomsFee2026,
    determineUnifiedRate,
    horsePowerToKw,
    resolveUtilCoefficient2026PersonalM1,
)


def test_control_case_lexus_lx_600_uses_automatic_util_coefficient() -> None:
    result = calculatePersonalImportCustoms(
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

    assert result["customsValueRub"] == 11_654_940.8
    assert result["customsFee"] == 73_860
    assert result["unifiedRate"] == 5_594_371.58
    assert result["utilCoefficient"] == 178.44
    assert result["utilFee"] == 3_568_800
    assert result["total"] == 9_237_031.58


def test_horse_power_is_converted_to_kw_automatically() -> None:
    assert horsePowerToKw(415) == 305.23


def test_customs_fee_2026_over_10m_rub() -> None:
    fee, _ = determineCustomsFee2026(11_654_940.8)
    assert fee == 73_860


def test_unified_rate_for_new_car_148000_usd_3500_cc() -> None:
    unified_rate, _ = determineUnifiedRate(
        customs_value_rub=11_654_940.8,
        customs_value_eur=128_037,
        engine_cc=3500,
        eur_to_rub_rate=91.0279,
        age_category="LE_3",
    )

    assert unified_rate == 5_594_371.58


def test_util_coefficient_2026_3001_3500_cc_and_294_21_316_26_kw() -> None:
    coefficient, _, matched_engine_range_cc, matched_power_range_kw = resolveUtilCoefficient2026PersonalM1(
        powertrain_kind="ICE",
        age_years=1,
        power_kw=305.23,
        engine_cc=3500,
    )

    assert coefficient == 178.44
    assert matched_engine_range_cc == "3001–3500 cc"
    assert matched_power_range_kw == "294.21–316.26 kW"


def test_boundary_fix_3000_cc_stays_in_2001_3000_cc_band() -> None:
    coefficient, _, matched_engine_range_cc, matched_power_range_kw = resolveUtilCoefficient2026PersonalM1(
        powertrain_kind="ICE",
        age_years=1,
        power_kw=369.96,
        engine_cc=3000,
    )

    assert coefficient == 172.44
    assert matched_engine_range_cc == "2001–3000 cc"
    assert matched_power_range_kw == "≥ 367.76 kW"


def test_full_calculation_87500_usd_3000_cc_503_hp_age_1() -> None:
    result = calculatePersonalImportCustoms(
        {
            "price": 87_500,
            "currencyToRubRate": 78.7496,
            "eurToRubRate": 91.0279,
            "engineCc": 3000,
            "horsePower": 503,
            "ageYears": 1,
            "isPersonalUse": True,
            "powertrainKind": "ICE",
        }
    )

    assert result["customsValueRub"] == 6_890_590
    assert result["customsFee"] == 49_240
    assert result["unifiedRate"] == 3_307_483.2
    assert result["utilCoefficient"] == 172.44
    assert result["utilFee"] == 3_448_800
    assert result["total"] == 6_805_523.2


def test_low_power_new_ice_car_gets_0_17_coefficient() -> None:
    result = calculatePersonalImportCustoms(
        {
            "price": 10_000,
            "currencyToRubRate": 78,
            "eurToRubRate": 91,
            "engineCc": 1000,
            "horsePower": 100,
            "ageYears": 1,
            "isPersonalUse": True,
            "powertrainKind": "ICE",
        }
    )

    assert result["utilCoefficient"] == 0.17
    assert result["utilFee"] == 3400


def test_low_power_used_ice_car_gets_0_26_coefficient() -> None:
    result = calculatePersonalImportCustoms(
        {
            "price": 10_000,
            "currencyToRubRate": 78,
            "eurToRubRate": 91,
            "engineCc": 1000,
            "horsePower": 100,
            "ageYears": 4,
            "isPersonalUse": True,
            "powertrainKind": "ICE",
        }
    )

    assert result["utilCoefficient"] == 0.26
    assert result["utilFee"] == 5200


def test_ev_calculation_allows_zero_engine_volume() -> None:
    result = calculatePersonalImportCustoms(
        {
            "price": 52_590,
            "currencyToRubRate": 91,
            "eurToRubRate": 98,
            "engineCc": 0,
            "horsePower": 300,
            "ageYears": 2,
            "isPersonalUse": True,
            "powertrainKind": "EV",
        }
    )

    assert result["customsFee"] > 0
    assert result["unifiedRate"] > 0
    assert result["utilCoefficient"] > 0
    assert result["details"]["powertrainKind"] == "EV"