from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mileon_saas.config import settings
from mileon_saas.db import get_session
from mileon_saas.models import CarListing
from mileon_saas.schemas import CarListingCreate, CarListingRead, ListingWithScores
from mileon_saas.services.decision_engine import evaluate_listing
from mileon_saas.services.ingestion import ingest_from_json
from mileon_saas.services.telegram_bot import send_top5_alert

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=list[ListingWithScores])
async def list_listings(
    company_id: int = settings.default_company_id,
    brand: Optional[str] = None,
    with_scores: bool = True,
    limit: int = 500,  # Default limit to prevent loading all records
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    query = select(CarListing).where(CarListing.company_id == company_id)
    if brand:
        query = query.where(CarListing.brand == brand)
    
    # Add ordering by ID descending to get newest first, then pagination
    query = query.order_by(CarListing.id.desc()).limit(limit).offset(offset)

    listings = (await session.scalars(query)).all()
    results = []
    for listing in listings:
        if with_scores:
            scores = await evaluate_listing(session, listing)
            results.append(ListingWithScores(listing=CarListingRead.model_validate(listing), scores=scores))
        else:
            results.append(ListingWithScores(
                listing=CarListingRead.model_validate(listing),
                scores=None,
            ))

    return results


@router.get("/{listing_id}", response_model=CarListingRead)
async def get_listing(listing_id: int, session: AsyncSession = Depends(get_session)):
    listing = await session.get(CarListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.post("", response_model=CarListingRead)
async def create_listing(
    payload: CarListingCreate,
    session: AsyncSession = Depends(get_session),
):
    listing = CarListing(**payload.model_dump())
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return listing


@router.post("/send-top5-telegram")
async def send_top5_telegram(
    company_id: int = settings.default_company_id,
    limit: int = 500,
    session: AsyncSession = Depends(get_session),
):
    """Send TOP-5 best deals to Telegram subscribers."""
    try:
        # Get top listings by buy_score
        query = select(CarListing).where(CarListing.company_id == company_id)
        query = query.order_by(CarListing.id.desc()).limit(limit)

        listings = (await session.scalars(query)).all()
        
        if not listings:
            return {
                "sent": 0,
                "top5_count": 0,
                "total_listings": 0,
            }
        
        # Evaluate and sort by buy_score
        results = []
        for listing in listings:
            try:
                scores = await evaluate_listing(session, listing)
                results.append({
                    "listing": CarListingRead.model_validate(listing),
                    "scores": scores,
                    "brand": listing.brand,
                    "model": listing.model,
                    "year": listing.year,
                    "price_usd": listing.price_usd,
                    "buy_score": scores.get("buy_score", 0),
                    "deal_score": scores.get("deal_score", 0),
                    "roi_percent": scores.get("roi_percent", 0),
                })
            except Exception as e:
                import logging
                logging.warning(f"Failed to evaluate listing {listing.id}: {e}")
                continue
        
        if not results:
            return {
                "sent": 0,
                "top5_count": 0,
                "total_listings": len(listings),
            }
        
        # Sort by buy_score descending
        results.sort(key=lambda x: x["buy_score"], reverse=True)
        
        # Send TOP-5 to Telegram
        sent = await send_top5_alert(session, company_id, results, role="buyer")
        
        return {
            "sent": sent,
            "top5_count": min(5, len(results)),
            "total_listings": len(listings),
        }
    except Exception as e:
        import logging
        logging.exception(f"Error in send_top5_telegram: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/ingest")
async def ingest_listings(
    path: str = "cars_data.json",
    company_id: int = settings.default_company_id,
    session: AsyncSession = Depends(get_session),
):
    count = await ingest_from_json(session, path, company_id)
    return {"ingested": count}
