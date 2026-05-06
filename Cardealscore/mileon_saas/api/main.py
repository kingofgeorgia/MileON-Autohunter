from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.config import settings
from mileon_saas.db import get_session, init_db
from mileon_saas.api.routes import admin, decisions, listings
from mileon_saas.services.telegram_bot import handle_update

app = FastAPI(title=settings.app_name)

app.include_router(listings.router, prefix="/api")
app.include_router(decisions.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post(settings.telegram_webhook_path)
async def telegram_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    secret = settings.telegram_webhook_secret
    if secret:
        header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_token != secret:
            raise HTTPException(status_code=403, detail="Invalid webhook token")

    payload = await request.json()
    await handle_update(session, payload)
    return JSONResponse({"ok": True})
