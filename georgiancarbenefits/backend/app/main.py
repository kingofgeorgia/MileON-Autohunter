from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.calculator import router as calculator_router
from app.api.cars import router as cars_router
from app.api.history import router as history_router

app = FastAPI(
    title="Georgian Car Benefits API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(calculator_router)
app.include_router(cars_router)
app.include_router(history_router)


@app.get("/health")
def health():
    return {"status": "ok"}
