import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from geoalchemy2.shape import from_shape

from app.database import get_db
from app.schemas.plot import LandPlotCreate, LandPlotResponse
from app.schemas.spatial_audit import SpatialAuditResponse
from app.models.land_plot import LandPlot
from app.utils.geo_utils import parse_plot_boundary
from app.services.spatial_engine import SpatialAnalysisEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/plots", tags=["Land Plots & Spatial Audits"])

@router.post("/", response_model=LandPlotResponse, status_code=status.HTTP_201_CREATED)
async def create_land_plot(plot_in: LandPlotCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates and persists a new land plot.
    Input boundary supports multiple flexible configurations (WKT, GeoJSON, or Lat/Lon coordinate array).
    """
    # 1. Parse and validate boundary geometry
    shapely_poly = parse_plot_boundary(plot_in.boundary)
    
    # 2. Compute plot area using UTM projection (EPSG:32647) for metric precision
    area_query = text("""
        SELECT ST_Area(ST_Transform(ST_GeomFromText(:wkt, 4326), 32647)) AS plot_area;
    """)
    area_res = await db.execute(area_query, {"wkt": shapely_poly.wkt})
    total_area_sqm = float(area_res.scalar() or 0.0)

    # 3. Create LandPlot record
    plot_record = LandPlot(
        plot_name=plot_in.plot_name,
        geom=from_shape(shapely_poly, srid=4326),
        total_area_sqm=total_area_sqm,
        address_text=plot_in.address_text
    )

    db.add(plot_record)
    await db.commit()
    await db.refresh(plot_record)
    return plot_record

@router.get("/{plot_id}", response_model=LandPlotResponse)
async def get_land_plot(plot_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve stored land plot metadata.
    """
    stmt = select(LandPlot).where(LandPlot.id == plot_id)
    result = await db.execute(stmt)
    plot = result.scalar_one_or_none()
    if not plot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Land plot with ID {plot_id} was not found in our records."
        )
    return plot

@router.post("/spatial-audit/{plot_id}", response_model=SpatialAuditResponse)
async def execute_spatial_audit(plot_id: int, db: AsyncSession = Depends(get_db)):
    """
    Runs automated PostGIS spatial intersection query to determine exactly
    which administrative urban zoning polygon(s) the plot falls into.
    """
    # 1. Fetch the plot
    stmt = select(LandPlot).where(LandPlot.id == plot_id)
    result = await db.execute(stmt)
    plot = result.scalar_one_or_none()
    if not plot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Land plot with ID {plot_id} was not found. Audit aborted."
        )

    # 2. Get polygon boundary WKT out of database geometry
    wkt_query = text("SELECT ST_AsText(geom) FROM land_plots WHERE id = :plot_id;")
    wkt_res = await db.execute(wkt_query, {"plot_id": plot_id})
    plot_wkt = wkt_res.scalar()

    # 3. Run spatial audit analysis
    audit_results = await SpatialAnalysisEngine.perform_spatial_audit(
        db=db,
        plot_id=plot_id,
        boundary_input=plot_wkt
    )
    return audit_results
