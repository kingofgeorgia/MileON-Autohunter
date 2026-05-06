from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.db import get_session
from mileon_saas.models import BrandPolicy, Company, TechnicalBlacklist, TelegramSubscription, User
from mileon_saas.schemas import (
    BrandPolicyCreate,
    BrandPolicyRead,
    CompanyCreate,
    CompanyRead,
    TechnicalBlacklistCreate,
    TechnicalBlacklistRead,
    UserCreate,
    UserRead,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/companies", response_model=CompanyRead)
async def create_company(payload: CompanyCreate, session: AsyncSession = Depends(get_session)):
    company = Company(**payload.model_dump())
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


@router.get("/companies", response_model=list[CompanyRead])
async def list_companies(session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(Company))).all()


@router.post("/users", response_model=UserRead)
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    user = User(**payload.model_dump())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/brand-policies", response_model=BrandPolicyRead)
async def create_brand_policy(payload: BrandPolicyCreate, session: AsyncSession = Depends(get_session)):
    policy = BrandPolicy(**payload.model_dump())
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    return policy


@router.get("/brand-policies", response_model=list[BrandPolicyRead])
async def list_brand_policies(session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(BrandPolicy))).all()


@router.post("/blacklist", response_model=TechnicalBlacklistRead)
async def create_blacklist(payload: TechnicalBlacklistCreate, session: AsyncSession = Depends(get_session)):
    entry = TechnicalBlacklist(**payload.model_dump())
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


@router.get("/blacklist", response_model=list[TechnicalBlacklistRead])
async def list_blacklist(session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(TechnicalBlacklist))).all()


@router.post("/telegram/subscriptions")
async def create_subscription(
    company_id: int,
    chat_id: str,
    role: str = "buyer",
    session: AsyncSession = Depends(get_session),
):
    subscription = TelegramSubscription(company_id=company_id, chat_id=chat_id, role=role)
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return {"id": subscription.id, "chat_id": subscription.chat_id, "role": subscription.role}
