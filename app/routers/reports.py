import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_db
from app.services.report_generator import ReportGeneratorService
from app.models.land_plot import LandPlot
from app.services.spatial_engine import SpatialAnalysisEngine
from app.services.far_osr_calculator import ZoningCalculatorService
from app.services.setback_analyzer import SetbackAnalysisService
from app.services.gemini_service import GeminiAIService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Feasibility PDF Report Generator"])

# Initialize Gemini AI service
gemini_service = GeminiAIService()

@router.get("/generate/{plot_id}", response_class=Response)
async def generate_plot_pdf_report(
    plot_id: int,
    proposed_development_type: str = "Residential Condominium",
    db: AsyncSession = Depends(get_db)
):
    """
    Synthesizes physical characteristics, PostGIS intersections, mathematical calculations,
    setback lines, and Gemini AI legal briefs to compile an elegant downloadable A4 PDF.
    """
    # 1. Fetch Plot
    stmt = select(LandPlot).where(LandPlot.id == plot_id)
    result = await db.execute(stmt)
    plot = result.scalar_one_or_none()
    if not plot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Land plot with ID {plot_id} was not found."
        )

    # Convert plot mapping
    plot_data = {
        "plot_name": plot.plot_name,
        "total_area_sqm": float(plot.total_area_sqm),
        "address_text": plot.address_text
    }

    # 2. Extract geometry WKT
    wkt_query = text("SELECT ST_AsText(geom) FROM land_plots WHERE id = :plot_id;")
    wkt_res = await db.execute(wkt_query, {"plot_id": plot_id})
    plot_wkt = wkt_res.scalar()

    # 3. Perform PostGIS spatial intersections
    audit_results = await SpatialAnalysisEngine.perform_spatial_audit(
        db=db,
        plot_id=plot_id,
        boundary_input=plot_wkt
    )
    
    intersecting_zones = audit_results.get("intersecting_zones", [])
    if not intersecting_zones:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected land plot does not intersect with any active zoning layer."
        )

    # 4. Perform FAR/OSR Capacity calculations
    calc_results = ZoningCalculatorService.calculate_development_capacity(
        plot_area_sqm=float(plot.total_area_sqm),
        intersecting_zones=intersecting_zones
    )

    # 5. Perform Setback envelope reduction calculations
    setback_results = await SetbackAnalysisService.analyze_setbacks(
        db=db,
        plot_id=plot_id,
        adjacent_road_width_m=6.0,
        boundary_setback_m=2.0
    )

    # 6. Generate Google Gemini AI report details
    ai_report_model = await gemini_service.analyze_zoning_impact(
        plot_area_sqm=float(plot.total_area_sqm),
        intersecting_zones=intersecting_zones,
        proposed_development_type=proposed_development_type
    )
    ai_report = ai_report_model.model_dump()

    # 7. Compile report binary bytes via WeasyPrint
    try:
        pdf_bytes = ReportGeneratorService.generate_pdf_report(
            plot_data=plot_data,
            audit_results=audit_results,
            calc_results=calc_results,
            setback_results=setback_results,
            ai_report=ai_report
        )
        
        # Return elegant stream response
        headers = {
            "Content-Disposition": f"attachment; filename=TOAT-Feasibility-Report-Plot-{plot_id}.pdf"
        }
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
        
    except Exception as e:
        logger.exception("Failed to compile WeasyPrint PDF layout.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate and compile PDF document: {str(e)}"
        )
