"""
Сервис курсов валют с кэшированием в памяти.
Использует open.er-api.com (бесплатный, без API-ключа).
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass
class _Cache:
    data: dict = field(default_factory=dict)
    fetched_at: float = 0.0


_cache = _Cache()
_lock = asyncio.Lock()


async def get_rates() -> dict[str, float]:
    """
    Возвращает словарь {currency_code: rate_to_rub}.
    Поддерживаемые коды: USD, EUR, GEL.
    """
    async with _lock:
        if _cache.data and (time.time() - _cache.fetched_at) < settings.exchange_cache_ttl_seconds:
            return _cache.data

        rates = await _fetch_rates()
        _cache.data = rates
        _cache.fetched_at = time.time()
        return rates


async def _fetch_rates() -> dict[str, float]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(settings.exchange_api_url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("result") != "success":
                raise ValueError(f"unexpected exchange API status: {data.get('result')}")

            r = data.get("rates") or {}
            if not all(code in r for code in ("RUB", "EUR", "GEL")):
                raise ValueError("exchange API response is missing one of RUB/EUR/GEL rates")

            usd_to_rub = float(r["RUB"])
            eur_to_rub = usd_to_rub / float(r["EUR"])
            gel_to_rub = usd_to_rub / float(r["GEL"])
            return {"USD": usd_to_rub, "EUR": eur_to_rub, "GEL": gel_to_rub}
    except Exception:
        logger.exception(
            "Exchange rates provider failed; falling back to static rates",
            extra={"exchange_api_url": settings.exchange_api_url},
        )
        # Fallback: использовать приблизительные значения, если API недоступен
        return {"USD": 91.0, "EUR": 98.0, "GEL": 33.0}


async def get_usd_to_rub() -> float:
    return (await get_rates())["USD"]


async def get_eur_to_rub() -> float:
    return (await get_rates())["EUR"]


async def get_gel_to_rub() -> float:
    return (await get_rates())["GEL"]


async def get_usd_to_eur() -> float:
    rates = await get_rates()
    return rates["EUR"] / rates["USD"]
