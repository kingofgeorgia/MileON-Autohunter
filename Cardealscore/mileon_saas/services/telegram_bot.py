from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.config import settings
from mileon_saas.models import ListingAction, TelegramSubscription


def _build_keyboard(listing_id: int) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "TAKEN", "callback_data": f"listing:{listing_id}:TAKEN"},
                {"text": "WATCHING", "callback_data": f"listing:{listing_id}:WATCHING"},
                {"text": "SKIP", "callback_data": f"listing:{listing_id}:SKIP"},
            ]
        ]
    }


def _build_alert_text(summary: dict[str, Any]) -> str:
    lines = [
        f"Status: {summary['decision']}",
        f"DealScore: {summary['deal_score']:.1f}",
        f"BuyScore: {summary['buy_score']:.1f}",
        f"Price: ${summary['price_usd']:.0f}",
        f"Expected Sell: ${summary['expected_sell_price']:.0f}",
        f"Net Profit: ${summary['net_profit']:.0f}",
        f"ROI: {summary['roi_percent']:.1f}%",
        f"Hold Days: {summary['expected_hold_days']}",
    ]
    if summary.get("risk_flags"):
        lines.append(f"Risk: {', '.join(summary['risk_flags'])}")
    return "\n".join(lines)


async def send_alert(session: AsyncSession, company_id: int, summary: dict[str, Any], role: str) -> int:
    if not settings.telegram_bot_token:
        return 0

    subscriptions = (await session.scalars(
        select(TelegramSubscription).where(
            TelegramSubscription.company_id == company_id,
            TelegramSubscription.role == role,
            TelegramSubscription.is_active.is_(True),
        )
    )).all()

    if not subscriptions:
        return 0

    text = _build_alert_text(summary)
    payload = {
        "text": text,
        "reply_markup": _build_keyboard(summary["listing_id"]),
    }

    sent = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for sub in subscriptions:
            payload["chat_id"] = sub.chat_id
            response = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json=payload,
            )
            if response.status_code == 200:
                sent += 1

    return sent


async def handle_update(session: AsyncSession, update: dict[str, Any]) -> None:
    callback = update.get("callback_query")
    if not callback:
        return

    data = callback.get("data", "")
    if not data.startswith("listing:"):
        return

    _, listing_id, action = data.split(":", 2)
    chat_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))
    if not listing_id or not chat_id:
        return

    session.add(ListingAction(listing_id=int(listing_id), chat_id=chat_id, action=action))
    await session.commit()


async def send_top5_alert(session: AsyncSession, company_id: int, listings: list[dict[str, Any]], role: str) -> int:
    """Send TOP-5 good deals to Telegram subscribers."""
    if not settings.telegram_bot_token:
        return 0

    subscriptions = (await session.scalars(
        select(TelegramSubscription).where(
            TelegramSubscription.company_id == company_id,
            TelegramSubscription.role == role,
            TelegramSubscription.is_active.is_(True),
        )
    )).all()

    if not subscriptions:
        return 0

    # Build TOP-5 message
    lines = ["🏆 <b>ТОП-5 ЛУЧШИХ ПРЕДЛОЖЕНИЙ</b>\n"]
    
    for idx, listing in enumerate(listings[:5], 1):
        brand = listing.get("brand", "Unknown")
        model = listing.get("model", "Unknown")
        year = listing.get("year", "N/A")
        price = listing.get("price_usd", 0)
        buy_score = listing.get("buy_score", 0)
        deal_score = listing.get("deal_score", 0)
        roi = listing.get("roi_percent", 0)
        
        lines.append(
            f"#{idx}. <b>{brand} {model}</b> ({year})\n"
            f"   💰 ${price:.0f} | 🎯 Buy: {buy_score:.1f} | 📊 Deal: {deal_score:.1f} | ROI: {roi:.1f}%\n"
        )
    
    text = "".join(lines)
    payload = {"text": text, "parse_mode": "HTML"}

    sent = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for sub in subscriptions:
            payload["chat_id"] = sub.chat_id
            response = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json=payload,
            )
            if response.status_code == 200:
                sent += 1

    return sent
