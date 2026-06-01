import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.setback import SetbackRequest, SetbackResponse
from app.services.setback_analyzer import SetbackAnalysisService
from app.models.land_plot import LandPlot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/setback", tags=["Construction Setback Analyzer"])

@router.post("/analyze", response_model=SetbackResponse)
async def analyze_plot_setbacks(
    req: SetbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Computes road setbacks and property boundary lines using PostGIS spatial buffers.
    Deduces the actual buildable envelope area and polygon coordinates.
    """
    # 1. Fetch Plot
    stmt = select(LandPlot).where(LandPlot.id == req.plot_id)
    result = await db.execute(stmt)
    plot = result.scalar_one_or_none()
    if not plot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Land plot with ID {req.plot_id} was not found."
        )

    # 2. Run Setback Engine
    try:
        results = await SetbackAnalysisService.analyze_setbacks(
            db=db,
            plot_id=req.plot_id,
            adjacent_road_width_m=req.adjacent_road_width_m,
            boundary_setback_m=req.boundary_setback_m
        )
        return results
    except Exception as e:
        logger.exception("Failed to calculate spatial setbacks.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate building envelope: {str(e)}"
        )
