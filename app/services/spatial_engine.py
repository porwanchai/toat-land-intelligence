import logging
import time
from typing import List, Dict, Any, Union
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from shapely.geometry import Polygon

from app.utils.geo_utils import parse_plot_boundary
from app.models.land_plot import LandPlot
from app.models.audit_log import SpatialAuditLog

logger = logging.getLogger(__name__)

class SpatialAnalysisEngine:
    @staticmethod
    async def perform_spatial_audit(
        db: AsyncSession,
        plot_id: int,
        boundary_input: Union[str, List[Any], Dict[str, Any]],
        audited_by_user_id: int = None
    ) -> Dict[str, Any]:
        """
        Executes precision PostGIS spatial intersection query.
        Calculates:
        - Exact intersecting administrative zoning polygons.
        - Precision metric intersection area (sqm) inside each zone by reprojecting to local Thailand coordinate system EPSG:32647.
        - Exact percentage coverage metrics.
        - Spatial geometry contours for UI overlay (returned as GeoJSON geometries).
        - Audit logs performance telemetry.
        """
        start_time = time.perf_counter()
        
        # 1. Parse & validate boundary polygon coordinates
        shapely_poly = parse_plot_boundary(boundary_input)
        plot_wkt = shapely_poly.wkt

        # 2. Optimized SQL Spatial Intersections
        # Storing data in EPSG:4326. We transform to EPSG:32647 (Thailand UTM Zone 47N)
        # to guarantee accurate square meter area computations without spherical distortion.
        query = text("""
            SELECT 
                uzl.id,
                uzl.zoning_color_code,
                uzl.zone_type_name,
                uzl.far_limit,
                uzl.osr_limit,
                uzl.construction_restrictions_text,
                uzl.published_fiscal_year,
                
                -- Calculate precise area (sqm) by reprojecting polygons to EPSG:32647
                ST_Area(
                    ST_Intersection(
                        ST_Transform(uzl.geom, 32647),
                        ST_Transform(ST_GeomFromText(:plot_wkt, 4326), 32647)
                    )
                ) AS intersection_area_sqm,
                
                -- Calculate percentage coverage on plot
                ROUND(
                    (ST_Area(
                        ST_Intersection(
                            ST_Transform(uzl.geom, 32647),
                            ST_Transform(ST_GeomFromText(:plot_wkt, 4326), 32647)
                        )
                    ) / 
                    ST_Area(
                        ST_Transform(ST_GeomFromText(:plot_wkt, 4326), 32647)
                    )) * 100.0,
                    2
                ) AS coverage_percentage,
                
                -- Return overlay GeoJSON geometry
                ST_AsGeoJSON(ST_Transform(uzl.geom, 4326)) AS zone_geojson,
                ST_AsGeoJSON(
                    ST_Transform(
                        ST_Intersection(
                            uzl.geom,
                            ST_GeomFromText(:plot_wkt, 4326)
                        ),
                        4326
                    )
                ) AS intersection_geojson
            FROM urban_zoning_layers uzl
            WHERE ST_Intersects(
                uzl.geom,
                ST_GeomFromText(:plot_wkt, 4326)
            )
            AND uzl.is_active = TRUE
            ORDER BY intersection_area_sqm DESC;
        """)

        # Execute
        result = await db.execute(query, {"plot_wkt": plot_wkt})
        rows = result.fetchall()

        # Calculate absolute plot area in square meters
        area_query = text("""
            SELECT ST_Area(ST_Transform(ST_GeomFromText(:plot_wkt, 4326), 32647)) AS plot_area;
        """)
        area_res = await db.execute(area_query, {"plot_wkt": plot_wkt})
        total_plot_area_sqm = float(area_res.scalar() or 0.0)

        # 3. Assemble response payload
        intersecting_zones = []
        for r in rows:
            intersecting_zones.append({
                "layer_id": r.id,
                "zoning_color_code": r.zoning_color_code,
                "zone_type_name": r.zone_type_name,
                "far_limit": float(r.far_limit) if r.far_limit is not None else None,
                "osr_limit": float(r.osr_limit) if r.osr_limit is not None else None,
                "construction_restrictions_text": r.construction_restrictions_text,
                "published_fiscal_year": r.published_fiscal_year,
                "intersection_area_sqm": float(r.intersection_area_sqm),
                "coverage_percentage": float(r.coverage_percentage),
                "zone_geojson": r.zone_geojson,
                "intersection_geojson": r.intersection_geojson
            })

        # Calculate execution metrics
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)

        audit_payload = {
            "plot_id": plot_id,
            "total_plot_area_sqm": total_plot_area_sqm,
            "intersecting_zones": intersecting_zones,
            "execution_time_ms": execution_time_ms
        }

        # 4. Save audit log telemetry
        audit_log = SpatialAuditLog(
            plot_id=plot_id,
            intersection_results=audit_payload,
            execution_time_ms=execution_time_ms,
            audited_by_user_id=audited_by_user_id
        )
        db.add(audit_log)
        await db.commit()

        return audit_payload
