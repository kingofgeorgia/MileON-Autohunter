from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.db import get_session
from mileon_saas.models import CarListing
from mileon_saas.schemas import ListingScores
from mileon_saas.services.decision_engine import evaluate_listing

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("/{listing_id}", response_model=ListingScores)
async def get_decision(listing_id: int, session: AsyncSession = Depends(get_session)):
    listing = await session.get(CarListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return await evaluate_listing(session, listing)
