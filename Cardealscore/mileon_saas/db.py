from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from mileon_saas.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def close_engine() -> None:
    """Completely close all database connections"""
    await engine.dispose()


async def init_engine() -> None:
    """Reinitialize the engine (for after database recreation)"""
    global engine
    # Dispose existing connections
    await engine.dispose()


async def init_db() -> None:
    # Dispose of any existing connections to allow database recreation
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
