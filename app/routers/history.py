import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.schemas.history import HistoryTimelineResponse
from app.services.history_tracker import ZoningHistoryTrackerService
from app.models.land_plot import LandPlot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/history", tags=["Historical Zoning Tracker"])

@router.get("/plot/{plot_id}", response_model=List[HistoryTimelineResponse])
async def get_plot_zoning_history(
    plot_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns complete chronological timeline changes of regulatory boundaries that
    have affected the given land plot coordinates over the fiscal years.
    """
    # 1. Validate Plot
    from sqlalchemy import select
    stmt = select(LandPlot).where(LandPlot.id == plot_id)
    result = await db.execute(stmt)
    plot = result.scalar_one_or_none()
    if not plot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Land plot with ID {plot_id} was not found."
        )

    # 2. Query timeline data
    timeline = await ZoningHistoryTrackerService.get_plot_historical_timeline(db, plot_id)
    return timeline
