import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_db
from app.schemas.calculator import CalculatorRequest, CalculatorResponse
from app.services.far_osr_calculator import ZoningCalculatorService
from app.models.land_plot import LandPlot
from app.services.spatial_engine import SpatialAnalysisEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calculator", tags=["Zoning Capacity Calculator"])

@router.post("/far-osr", response_model=CalculatorResponse)
async def calculate_far_osr_capacity(
    req: CalculatorRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns precise weighted building capacity stats (Max GFA, Min Open Space, max stories)
    for a given land plot across intersecting administrative zones.
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

    # 2. Extract geometry WKT
    wkt_query = text("SELECT ST_AsText(geom) FROM land_plots WHERE id = :plot_id;")
    wkt_res = await db.execute(wkt_query, {"plot_id": req.plot_id})
    plot_wkt = wkt_res.scalar()

    # 3. Perform PostGIS spatial audit to gather precise intersecting zones data
    audit_results = await SpatialAnalysisEngine.perform_spatial_audit(
        db=db,
        plot_id=req.plot_id,
        boundary_input=plot_wkt
    )
    
    intersecting_zones = audit_results.get("intersecting_zones", [])
    if not intersecting_zones:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected land plot does not intersect with any administrative zoning layer in our database."
        )

    # 4. Compute building capacities
    calc_results = ZoningCalculatorService.calculate_development_capacity(
        plot_area_sqm=float(plot.total_area_sqm),
        intersecting_zones=intersecting_zones
    )
    return calc_results
