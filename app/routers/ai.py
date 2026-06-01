import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_db
from app.schemas.ai_analysis import ZoningImpactRequest, QuickSummaryRequest
from app.services.gemini_service import GeminiAIService, ZoningFeasibilityReport
from app.models.land_plot import LandPlot
from app.services.spatial_engine import SpatialAnalysisEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Processing Engine (Gemini)"])

# Initialize service
gemini_service = GeminiAIService()

@router.post("/analyze-zoning-impact", response_model=ZoningFeasibilityReport)
async def analyze_zoning_impact(
    req: ZoningImpactRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers automated AI urban zoning feasibility audit.
    Fetches precision spatial intersection statistics, maps legislative rules,
    and returns a structured development report via Google Gemini.
    """
    # 1. Fetch Land Plot
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
            detail="The selected land plot does not intersect with any administrative zoning layer in our database. Ingestion required first."
        )

    # 4. Generate structured Gemini AI feasibility assessment
    report = await gemini_service.analyze_zoning_impact(
        plot_area_sqm=float(plot.total_area_sqm),
        intersecting_zones=intersecting_zones,
        proposed_development_type=req.proposed_development_type
    )
    return report

@router.post("/quick-summary")
async def quick_summary(req: QuickSummaryRequest, db: AsyncSession = Depends(get_db)):
    """
    Retrieves quick natural-language breakdown of a land plot's zoning context.
    """
    stmt = select(LandPlot).where(LandPlot.id == req.plot_id)
    result = await db.execute(stmt)
    plot = result.scalar_one_or_none()
    if not plot:
        raise HTTPException(status_code=404, detail="Land plot not found.")

    wkt_query = text("SELECT ST_AsText(geom) FROM land_plots WHERE id = :plot_id;")
    wkt_res = await db.execute(wkt_query, {"plot_id": req.plot_id})
    plot_wkt = wkt_res.scalar()

    audit_results = await SpatialAnalysisEngine.perform_spatial_audit(db, req.plot_id, plot_wkt)
    zones = audit_results.get("intersecting_zones", [])

    primary_zone = zones[0] if zones else {}
    summary = (
        f"ที่ดินขนาด {plot.total_area_sqm:.2f} ตร.ม. ตั้งอยู่ในพื้นที่ {primary_zone.get('zone_type_name', 'N/A')} "
        f"({primary_zone.get('zoning_color_code', 'N/A')}). ข้อจำกัด FAR อยู่ที่ {primary_zone.get('far_limit', 'N/A')} "
        f"และ OSR อยู่ที่ {primary_zone.get('osr_limit', 'N/A')}."
    )
    return {"summary": summary}
