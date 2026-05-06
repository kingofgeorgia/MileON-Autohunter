import asyncio
import html
import logging
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

import cloudscraper
import requests
import yaml
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("myauto_moscow_bot")


DEFAULT_CONFIG = {
    "myauto": {
        "base_api": "https://api2.myauto.ge",
        "languages": ["en", "ru", "ka"],
        "timeout": 30,
        "currency_map": {
            1: "USD",
            2: "GEL",
            3: "EUR",
        },
    },
    "exchange": {
        "fallback_usd_rub": 95.0,
        "fallback_eur_rub": 103.0,
        "fallback_gel_rub": 35.0,
    },
    "costs": {
        "fixed": [
            {"name": "Логистика Грузия → Москва", "amount_rub": 250000},
            {"name": "Таможенный брокер / оформление", "amount_rub": 35000},
            {"name": "СБКТС + ЭПТС", "amount_rub": 55000},
            {"name": "СВХ / терминал / выдача", "amount_rub": 18000},
            {"name": "Прочие расходы", "amount_rub": 12000},
        ]
    },
    "tariffs": {
        "customs_fee_rub_bands": [
            {"max_value_rub": 200000, "fee_rub": 1067},
            {"max_value_rub": 450000, "fee_rub": 2134},
            {"max_value_rub": 1200000, "fee_rub": 4269},
            {"max_value_rub": 2700000, "fee_rub": 11746},
            {"max_value_rub": 4200000, "fee_rub": 16524},
            {"max_value_rub": 5500000, "fee_rub": 21344},
            {"max_value_rub": 7000000, "fee_rub": 27540},
            {"max_value_rub": 8000000, "fee_rub": 30000},
            {"max_value_rub": 9000000, "fee_rub": 30000},
            {"max_value_rub": 10000000, "fee_rub": 30000},
            {"max_value_rub": 9999999999, "fee_rub": 30000},
        ],
        "used_auto_duty": {
            "age_rules": [
                {
                    "min_years": 0,
                    "max_years": 3,
                    "mode": "percent_or_min_per_cc",
                    "percent": 0.48,
                    "min_eur_per_cc_bands": [
                        {"up_to_engine_cc": 1000, "eur_per_cc": 1.5},
                        {"up_to_engine_cc": 1500, "eur_per_cc": 1.7},
                        {"up_to_engine_cc": 1800, "eur_per_cc": 2.5},
                        {"up_to_engine_cc": 2300, "eur_per_cc": 2.7},
                        {"up_to_engine_cc": 3000, "eur_per_cc": 3.0},
                        {"up_to_engine_cc": 999999, "eur_per_cc": 3.6},
                    ],
                },
                {
                    "min_years": 3,
                    "max_years": 5,
                    "mode": "eur_per_cc",
                    "eur_per_cc_bands": [
                        {"up_to_engine_cc": 1000, "eur_per_cc": 1.5},
                        {"up_to_engine_cc": 1500, "eur_per_cc": 1.7},
                        {"up_to_engine_cc": 1800, "eur_per_cc": 2.5},
                        {"up_to_engine_cc": 2300, "eur_per_cc": 2.7},
                        {"up_to_engine_cc": 3000, "eur_per_cc": 3.0},
                        {"up_to_engine_cc": 999999, "eur_per_cc": 3.6},
                    ],
                },
                {
                    "min_years": 5,
                    "max_years": 100,
                    "mode": "eur_per_cc",
                    "eur_per_cc_bands": [
                        {"up_to_engine_cc": 1000, "eur_per_cc": 3.0},
                        {"up_to_engine_cc": 1500, "eur_per_cc": 3.2},
                        {"up_to_engine_cc": 1800, "eur_per_cc": 3.5},
                        {"up_to_engine_cc": 2300, "eur_per_cc": 4.8},
                        {"up_to_engine_cc": 3000, "eur_per_cc": 5.0},
                        {"up_to_engine_cc": 999999, "eur_per_cc": 5.7},
                    ],
                },
            ]
        },
        "util_fee": {
            "base_rub": 20000,
            "preferential": {
                "enabled": True,
                "max_hp": 160,
                "amount_rub": 3400,
            },
            "coefficient_bands": [
                {"up_to_engine_cc": 1000, "coefficient": 0.17},
                {"up_to_engine_cc": 2000, "coefficient": 0.26},
                {"up_to_engine_cc": 3000, "coefficient": 0.5},
                {"up_to_engine_cc": 3500, "coefficient": 0.89},
                {"up_to_engine_cc": 999999, "coefficient": 1.4},
            ],
        },
    },
}


FUEL_MAP = {
    1: "Дизель",
    2: "Бензин",
    3: "Гибрид",
    4: "Электро",
    5: "Газ",
    6: "Plug-in гибрид",
}

GEARBOX_MAP = {
    1: "Механика",
    2: "Tiptronic",
    3: "Автомат",
    4: "Вариатор",
    5: "Робот",
}

DRIVE_MAP = {
    1: "Передний",
    2: "Задний",
    3: "Полный",
}


def deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str) -> dict:
    config = DEFAULT_CONFIG
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        config = deep_merge(DEFAULT_CONFIG, loaded)
    return config


def fmt_money(value: float | int) -> str:
    return f"{int(round(value)):,}".replace(",", " ")


def fmt_float(value: float, digits: int = 2) -> str:
    text = f"{value:.{digits}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def to_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}, ()):
            return value
    return None


def extract_listing_id(text: str) -> Optional[int]:
    if not text:
        return None

    text = text.strip()

    direct = re.fullmatch(r"\d{6,12}", text)
    if direct:
        return int(direct.group(0))

    patterns = [
        r"/pr/(\d{6,12})",
        r"/products/(\d{6,12})",
        r"car_id[=/](\d{6,12})",
        r"\b(\d{6,12})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def iter_dicts(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from iter_dicts(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_dicts(item)


@dataclass
class Listing:
    listing_id: int
    year: Optional[int]
    price: Optional[float]
    price_usd: Optional[float]
    currency_id: Optional[int]
    currency_code: Optional[str]
    engine_cc: Optional[int]
    mileage_km: Optional[int]
    fuel_type_id: Optional[int]
    fuel_name: Optional[str]
    gearbox_type_id: Optional[int]
    gearbox_name: Optional[str]
    drive_type_id: Optional[int]
    drive_name: Optional[str]
    customs_passed: Optional[bool]
    man_id: Optional[int]
    model_id: Optional[int]
    man_name: Optional[str]
    model_name: Optional[str]
    raw_model_text: Optional[str]
    hp: Optional[int]
    vin: Optional[str]
    seller_name: Optional[str]
    seller_phone_masked: Optional[str]
    color_id: Optional[int]
    raw: dict

    @property
    def title(self) -> str:
        parts = []
        if self.man_name:
            parts.append(self.man_name)
        if self.model_name:
            parts.append(self.model_name)
        elif self.raw_model_text:
            parts.append(self.raw_model_text)
        title = " ".join(part.strip() for part in parts if part and str(part).strip())
        return title or f"Объявление {self.listing_id}"


class MyAutoAPI:
    def __init__(self, config: dict):
        myauto_cfg = config.get("myauto", {})
        self.base_api = myauto_cfg.get("base_api", "https://api2.myauto.ge").rstrip("/")
        self.languages = myauto_cfg.get("languages", ["en", "ru", "ka"])
        self.timeout = int(myauto_cfg.get("timeout", 30))
        self.currency_map = {
            int(k): v for k, v in (myauto_cfg.get("currency_map", {}) or {}).items()
        }
        self.debug = os.getenv("MYAUTO_DEBUG", "0").strip() == "1"

        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self.scraper.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
                "Origin": "https://www.myauto.ge",
                "Referer": "https://www.myauto.ge/",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/137.0.0.0 Safari/537.36"
                ),
            }
        )

    def _log(self, message: str) -> None:
        if self.debug:
            logger.info(message)

    def _url(self, language: str, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        return f"{self.base_api}/{language}/{endpoint}"

    def _get_json(self, language: str, endpoint: str, params: Optional[dict] = None) -> dict:
        url = self._url(language, endpoint)
        self._log(f"MyAuto GET {url} params={params}")
        resp = self.scraper.get(url, params=params, timeout=self.timeout)
        self._log(f"MyAuto status {resp.status_code} for {url}")
        resp.raise_for_status()
        return resp.json()

    def fetch_listing(self, listing_id: int) -> Listing:
        last_error: Optional[Exception] = None

        for language in self.languages:
            try:
                payload = self._get_json(language, f"products/{listing_id}")
                listing = self._parse_listing_payload(payload)
                man_name = self._resolve_man_name(listing.man_id, language)
                model_name = self._resolve_model_name(listing.man_id, listing.model_id, language)

                listing.man_name = man_name or listing.man_name
                listing.model_name = model_name or listing.model_name
                return listing
            except Exception as exc:
                last_error = exc
                self._log(f"Detail endpoint failed for lang={language}: {exc}")

        for language in self.languages:
            try:
                payload = self._get_json(
                    language,
                    "products",
                    params={"ProductID": listing_id, "Page": 1},
                )
                listing = self._parse_listing_from_list_payload(payload, listing_id)
                man_name = self._resolve_man_name(listing.man_id, language)
                model_name = self._resolve_model_name(listing.man_id, listing.model_id, language)

                listing.man_name = man_name or listing.man_name
                listing.model_name = model_name or listing.model_name
                return listing
            except Exception as exc:
                last_error = exc
                self._log(f"List endpoint failed for lang={language}: {exc}")

        if last_error:
            raise RuntimeError(f"Не удалось получить объявление {listing_id}: {last_error}") from last_error
        raise RuntimeError(f"Не удалось получить объявление {listing_id}")

    def _parse_listing_payload(self, payload: dict) -> Listing:
        data = payload.get("data") or {}
        info = data.get("info") or {}

        if not info:
            raise ValueError("В ответе MyAuto отсутствует data.info")

        listing_id = to_int(first_non_empty(info.get("car_id"), info.get("id")))
        if not listing_id:
            raise ValueError("Не удалось определить ID объявления")

        currency_id = to_int(info.get("currency_id"))
        return Listing(
            listing_id=listing_id,
            year=to_int(info.get("prod_year")),
            price=to_float(info.get("price")),
            price_usd=to_float(info.get("price_usd")),
            currency_id=currency_id,
            currency_code=self.currency_map.get(currency_id),
            engine_cc=to_int(info.get("engine_volume")),
            mileage_km=to_int(first_non_empty(info.get("car_run_km"), info.get("car_run"))),
            fuel_type_id=to_int(info.get("fuel_type_id")),
            fuel_name=FUEL_MAP.get(to_int(info.get("fuel_type_id"))),
            gearbox_type_id=to_int(info.get("gear_type_id")),
            gearbox_name=GEARBOX_MAP.get(to_int(info.get("gear_type_id"))),
            drive_type_id=to_int(info.get("drive_type_id")),
            drive_name=DRIVE_MAP.get(to_int(info.get("drive_type_id"))),
            customs_passed=bool(info.get("customs_passed")) if info.get("customs_passed") is not None else None,
            man_id=to_int(info.get("man_id")),
            model_id=to_int(info.get("model_id")),
            man_name=None,
            model_name=None,
            raw_model_text=first_non_empty(info.get("car_model"), info.get("trim_name")),
            hp=to_int(info.get("hp")),
            vin=(info.get("vin") or "").strip() or None,
            seller_name=info.get("client_name"),
            seller_phone_masked=info.get("client_phone"),
            color_id=to_int(info.get("color_id")),
            raw=info,
        )

    def _parse_listing_from_list_payload(self, payload: dict, listing_id: int) -> Listing:
        data = payload.get("data") or {}
        items = data.get("items") or []
        if not isinstance(items, list) or not items:
            raise ValueError("В ответе MyAuto отсутствует data.items")

        target_item = None
        for item in items:
            current_id = to_int(
                first_non_empty(item.get("car_id"), item.get("id"), item.get("product_id"))
            )
            if current_id == listing_id:
                target_item = item
                break

        if target_item is None:
            target_item = items[0]

        fake_payload = {"data": {"info": target_item}}
        return self._parse_listing_payload(fake_payload)

    @lru_cache(maxsize=16)
    def _get_mans_payload(self, language: str) -> dict:
        return self._get_json(language, "vehicle/mans")

    @lru_cache(maxsize=64)
    def _get_models_payload(self, language: str, man_id: int) -> dict:
        return self._get_json(language, "vehicle/models", params={"man_id": man_id})

    def _resolve_man_name(self, man_id: Optional[int], language: str) -> Optional[str]:
        if not man_id:
            return None
        try:
            payload = self._get_mans_payload(language)
            return self._find_name_by_id(
                payload=payload,
                target_id=man_id,
                id_keys=("man_id", "id"),
                name_keys=("man_name", "title", "name", "value", "text"),
            )
        except Exception as exc:
            self._log(f"Manufacturer lookup failed: {exc}")
            return None

    def _resolve_model_name(
        self,
        man_id: Optional[int],
        model_id: Optional[int],
        language: str,
    ) -> Optional[str]:
        if not man_id or not model_id:
            return None
        try:
            payload = self._get_models_payload(language, man_id)
            return self._find_name_by_id(
                payload=payload,
                target_id=model_id,
                id_keys=("model_id", "id"),
                name_keys=("model_name", "title", "name", "value", "text"),
            )
        except Exception as exc:
            self._log(f"Model lookup failed: {exc}")
            return None

    def _find_name_by_id(
        self,
        payload: dict,
        target_id: int,
        id_keys: tuple[str, ...],
        name_keys: tuple[str, ...],
    ) -> Optional[str]:
        for item in iter_dicts(payload):
            for id_key in id_keys:
                current_id = to_int(item.get(id_key))
                if current_id == target_id:
                    for name_key in name_keys:
                        value = item.get(name_key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()
        return None


class ExchangeRates:
    def __init__(self, config: dict):
        exchange_cfg = config.get("exchange", {})
        self.fallback_usd_rub = float(exchange_cfg.get("fallback_usd_rub", 95.0))
        self.fallback_eur_rub = float(exchange_cfg.get("fallback_eur_rub", 103.0))
        self.fallback_gel_rub = float(exchange_cfg.get("fallback_gel_rub", 35.0))
        self.timeout = 20

    @staticmethod
    def _parse_cbr_xml(xml_text: str) -> dict[str, float]:
        result: dict[str, float] = {}
        pattern = re.compile(
            r"<CharCode>(?P<code>[A-Z]{3})</CharCode>.*?<Nominal>(?P<nominal>\d+)</Nominal>.*?<Value>(?P<value>[\d,]+)</Value>",
            re.S,
        )
        for match in pattern.finditer(xml_text):
            code = match.group("code")
            nominal = float(match.group("nominal"))
            value = float(match.group("value").replace(",", "."))
            result[code] = value / nominal
        return result

    def get_rates(self) -> dict[str, float]:
        try:
            resp = requests.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=self.timeout)
            resp.raise_for_status()
            parsed = self._parse_cbr_xml(resp.text)
            rates = {
                "RUB": 1.0,
                "USD": parsed.get("USD", self.fallback_usd_rub),
                "EUR": parsed.get("EUR", self.fallback_eur_rub),
                "GEL": parsed.get("GEL", self.fallback_gel_rub),
            }
            return rates
        except Exception as exc:
            logger.warning("Не удалось получить курсы ЦБ РФ, использую fallback: %s", exc)
            return {
                "RUB": 1.0,
                "USD": self.fallback_usd_rub,
                "EUR": self.fallback_eur_rub,
                "GEL": self.fallback_gel_rub,
            }


class CustomsCalculator:
    def __init__(self, config: dict):
        self.config = config
        self.tariffs = config.get("tariffs", {})
        self.fixed_costs = config.get("costs", {}).get("fixed", [])

    @staticmethod
    def calc_vehicle_age(year: int) -> int:
        now_year = datetime.now(timezone.utc).year
        return max(0, now_year - year)

    @staticmethod
    def _pick_band(bands: list[dict], key: str, value: float) -> dict:
        for band in bands:
            limit = float(band.get(key, 0))
            if value <= limit:
                return band
        return bands[-1]

    def _calc_customs_fee(self, customs_value_rub: float) -> float:
        bands = self.tariffs.get("customs_fee_rub_bands", [])
        if not bands:
            return 0.0
        band = self._pick_band(bands, "max_value_rub", customs_value_rub)
        return float(band.get("fee_rub", 0))

    def _find_age_rule(self, age_years: int) -> dict:
        rules = (
            self.tariffs.get("used_auto_duty", {}).get("age_rules", [])
        )
        if not rules:
            raise ValueError("В config.yaml отсутствуют tariffs.used_auto_duty.age_rules")
        for rule in rules:
            min_years = int(rule.get("min_years", 0))
            max_years = int(rule.get("max_years", 999))
            if min_years <= age_years < max_years:
                return rule
        return rules[-1]

    def _calc_duty_rub(
        self,
        price_usd: float,
        engine_cc: int,
        year: int,
        usd_rub: float,
        eur_rub: float,
    ) -> tuple[float, str]:
        age_years = self.calc_vehicle_age(year)
        rule = self._find_age_rule(age_years)
        mode = rule.get("mode")

        price_rub = price_usd * usd_rub
        price_eur = price_rub / eur_rub if eur_rub else 0

        if mode == "percent_or_min_per_cc":
            percent = float(rule.get("percent", 0))
            percent_value_eur = price_eur * percent
            bands = rule.get("min_eur_per_cc_bands", [])
            if not bands:
                raise ValueError("Нет min_eur_per_cc_bands для percent_or_min_per_cc")
            band = self._pick_band(bands, "up_to_engine_cc", engine_cc)
            min_value_eur = engine_cc * float(band.get("eur_per_cc", 0))
            duty_eur = max(percent_value_eur, min_value_eur)
            formula = (
                f"max({fmt_float(price_eur)} € × {fmt_float(percent * 100)}%, "
                f"{engine_cc} см³ × {fmt_float(float(band.get('eur_per_cc', 0)))} €/см³)"
            )
            return duty_eur * eur_rub, formula

        if mode == "eur_per_cc":
            bands = rule.get("eur_per_cc_bands", [])
            if not bands:
                raise ValueError("Нет eur_per_cc_bands для eur_per_cc")
            band = self._pick_band(bands, "up_to_engine_cc", engine_cc)
            rate = float(band.get("eur_per_cc", 0))
            duty_eur = engine_cc * rate
            formula = f"{engine_cc} см³ × {fmt_float(rate)} €/см³"
            return duty_eur * eur_rub, formula

        raise ValueError(f"Неизвестный mode расчёта пошлины: {mode}")

    def _calc_util_fee_rub(self, listing: Listing) -> tuple[float, str]:
        util_cfg = self.tariffs.get("util_fee", {})
        base_rub = float(util_cfg.get("base_rub", 20000))

        preferential_cfg = util_cfg.get("preferential", {})
        preferential_enabled = bool(preferential_cfg.get("enabled", False))
        preferential_max_hp = int(preferential_cfg.get("max_hp", 0))
        preferential_amount = float(preferential_cfg.get("amount_rub", 0))

        if preferential_enabled and listing.hp and listing.hp > 0 and listing.hp <= preferential_max_hp:
            return preferential_amount, f"льготный фиксированный утиль (≤ {preferential_max_hp} л.с.)"

        bands = util_cfg.get("coefficient_bands", [])
        if not bands:
            return base_rub, "базовая ставка утильсбора"

        engine_cc = listing.engine_cc or 0
        band = self._pick_band(bands, "up_to_engine_cc", engine_cc)
        coefficient = float(band.get("coefficient", 1.0))
        return base_rub * coefficient, f"{fmt_float(base_rub)} ₽ × коэффициент {fmt_float(coefficient)}"

    def calculate(self, listing: Listing, rates: dict[str, float]) -> dict:
        if not listing.year:
            raise ValueError("Не указан год выпуска")
        if not listing.engine_cc:
            raise ValueError("Не указан объём двигателя")

        usd_rub = float(rates["USD"])
        eur_rub = float(rates["EUR"])

        price_usd = resolve_listing_price_usd(listing, rates)
        customs_value_rub = price_usd * usd_rub

        duty_rub, duty_formula = self._calc_duty_rub(
            price_usd=price_usd,
            engine_cc=listing.engine_cc,
            year=listing.year,
            usd_rub=usd_rub,
            eur_rub=eur_rub,
        )
        customs_fee_rub = self._calc_customs_fee(customs_value_rub)
        util_fee_rub, util_formula = self._calc_util_fee_rub(listing)

        fixed_cost_items = []
        fixed_cost_total = 0.0
        for item in self.fixed_costs:
            name = str(item.get("name", "Расход"))
            amount = float(item.get("amount_rub", 0))
            fixed_cost_items.append({"name": name, "amount_rub": amount})
            fixed_cost_total += amount

        total_rub = customs_value_rub + duty_rub + customs_fee_rub + util_fee_rub + fixed_cost_total

        return {
            "rates": rates,
            "age_years": self.calc_vehicle_age(listing.year),
            "price_usd": price_usd,
            "customs_value_rub": customs_value_rub,
            "duty_rub": duty_rub,
            "duty_formula": duty_formula,
            "customs_fee_rub": customs_fee_rub,
            "util_fee_rub": util_fee_rub,
            "util_formula": util_formula,
            "fixed_cost_items": fixed_cost_items,
            "fixed_cost_total": fixed_cost_total,
            "total_rub": total_rub,
        }


def resolve_listing_price_usd(listing: Listing, rates: dict[str, float]) -> float:
    if listing.price_usd and listing.price_usd > 0:
        return float(listing.price_usd)

    if listing.price and listing.price > 0:
        currency_code = listing.currency_code or "USD"
        if currency_code == "USD":
            return float(listing.price)
        if currency_code == "EUR":
            return float(listing.price) * rates["EUR"] / rates["USD"]
        if currency_code == "GEL":
            return float(listing.price) * rates["GEL"] / rates["USD"]

    raise ValueError("Не удалось определить цену в USD по данным объявления")


def build_result_text(listing: Listing, calc: dict) -> str:
    safe_title = html.escape(listing.title)
    details = [
        f"<b>{safe_title}</b>",
        f"ID объявления: <code>{listing.listing_id}</code>",
    ]

    subtitle_parts = []
    if listing.year:
        subtitle_parts.append(str(listing.year))
    if listing.engine_cc:
        subtitle_parts.append(f"{listing.engine_cc} см³")
    if listing.fuel_name:
        subtitle_parts.append(listing.fuel_name)
    if listing.gearbox_name:
        subtitle_parts.append(listing.gearbox_name)
    if listing.drive_name:
        subtitle_parts.append(listing.drive_name)
    if subtitle_parts:
        details.append(" • ".join(subtitle_parts))

    if listing.mileage_km:
        details.append(f"Пробег: {fmt_money(listing.mileage_km)} км")

    if listing.vin:
        details.append(f"VIN: <code>{html.escape(listing.vin)}</code>")

    if listing.customs_passed is not None:
        local_customs_note = "да" if listing.customs_passed else "нет"
        details.append(f"MyAuto customs_passed: {local_customs_note}")

    details.append("")
    details.append("<b>Расчёт до Москвы</b>")
    details.append(f"Цена на MyAuto: {fmt_money(calc['price_usd'])} $")
    details.append(f"Курс USD/₽: {fmt_float(calc['rates']['USD'], 4)}")
    details.append(f"Курс EUR/₽: {fmt_float(calc['rates']['EUR'], 4)}")
    details.append(f"Таможенная стоимость: {fmt_money(calc['customs_value_rub'])} ₽")
    details.append(
        f"Пошлина: {fmt_money(calc['duty_rub'])} ₽ "
        f"(<i>{html.escape(calc['duty_formula'])}</i>)"
    )
    details.append(f"Таможенный сбор: {fmt_money(calc['customs_fee_rub'])} ₽")
    details.append(
        f"Утильсбор: {fmt_money(calc['util_fee_rub'])} ₽ "
        f"(<i>{html.escape(calc['util_formula'])}</i>)"
    )

    if calc["fixed_cost_items"]:
        details.append("")
        details.append("<b>Прочие расходы</b>")
        for item in calc["fixed_cost_items"]:
            details.append(f"• {html.escape(item['name'])}: {fmt_money(item['amount_rub'])} ₽")
        details.append(f"Итого прочие расходы: {fmt_money(calc['fixed_cost_total'])} ₽")

    details.append("")
    details.append(f"<b>ИТОГО ДО МОСКВЫ: {fmt_money(calc['total_rub'])} ₽</b>")

    notes = []
    if not listing.hp or listing.hp <= 0:
        notes.append("В API MyAuto мощность не указана, утиль посчитан по конфигу и объёму двигателя.")
    if listing.raw_model_text and not listing.model_name:
        notes.append(f"Сырые данные модели из MyAuto: {listing.raw_model_text}")
    if notes:
        details.append("")
        details.append("<b>Примечания</b>")
        for note in notes:
            details.append(f"• {html.escape(note)}")

    return "\n".join(details)


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yaml").strip()

if not BOT_TOKEN:
    raise RuntimeError("В .env не указан BOT_TOKEN")

CONFIG = load_config(CONFIG_PATH)
MYAUTO_API = MyAutoAPI(CONFIG)
RATES_CLIENT = ExchangeRates(CONFIG)
CALCULATOR = CustomsCalculator(CONFIG)

dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    text = (
        "Отправь ID объявления MyAuto или полную ссылку.\n\n"
        "Примеры:\n"
        "<code>120908199</code>\n"
        "<code>https://www.myauto.ge/en/pr/120908199</code>"
    )
    await message.answer(text)


@dp.message(Command("help"))
async def help_handler(message: Message) -> None:
    text = (
        "Бот принимает:\n"
        "• ID объявления\n"
        "• ссылку на объявление MyAuto\n\n"
        "Что считает:\n"
        "• цену авто в ₽\n"
        "• пошлину\n"
        "• таможенный сбор\n"
        "• утильсбор\n"
        "• логистику и прочие расходы из config.yaml\n"
        "• итог до Москвы"
    )
    await message.answer(text)


def blocking_calculation(listing_id: int) -> tuple[Listing, dict]:
    listing = MYAUTO_API.fetch_listing(listing_id)
    rates = RATES_CLIENT.get_rates()
    calc = CALCULATOR.calculate(listing, rates)
    return listing, calc


@dp.message(F.text)
async def listing_handler(message: Message) -> None:
    text = (message.text or "").strip()
    listing_id = extract_listing_id(text)

    if not listing_id:
        await message.answer(
            "Не смог распознать ID объявления.\n"
            "Пришли число вроде <code>120908199</code> или полную ссылку MyAuto."
        )
        return

    wait_msg = await message.answer(f"Считаю объявление <code>{listing_id}</code>...")

    try:
        listing, calc = await asyncio.to_thread(blocking_calculation, listing_id)
        result_text = build_result_text(listing, calc)
        await wait_msg.edit_text(result_text)
    except Exception as exc:
        logger.exception("Ошибка расчёта по объявлению %s", listing_id)
        await wait_msg.edit_text(
            "Ошибка расчёта.\n"
            f"ID: <code>{listing_id}</code>\n"
            f"Текст ошибки: <code>{html.escape(str(exc))}</code>"
        )


async def main() -> None:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())