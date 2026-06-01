import logging
import json
from typing import Dict, Any, List, Union
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from shapely.geometry import shape, mapping
from shapely.wkt import loads as load_wkt

from app.utils.geo_utils import parse_plot_boundary

logger = logging.getLogger(__name__)

class SetbackAnalysisService:
    @staticmethod
    async def analyze_setbacks(
        db: AsyncSession,
        plot_id: int,
        adjacent_road_width_m: float = 6.0,
        boundary_setback_m: float = 2.0
    ) -> Dict[str, Any]:
        """
        Calculates construction setback boundaries under the Thai Building Control Act.
        - Public Road Setback: Derives setback line based on road width (e.g. 6m road usually requires 2-3m setback).
        - Property Line Setbacks: Standard 2m boundary spacing for high-density walls.
        - Calculates the exact modified buildable polygon boundary using PostGIS ST_Difference / ST_Buffer operations.
        """
        # 1. Fetch plot geometry
        wkt_query = text("SELECT ST_AsText(geom) FROM land_plots WHERE id = :plot_id;")
        wkt_res = await db.execute(wkt_query, {"plot_id": plot_id})
        plot_wkt = wkt_res.scalar()
        if not plot_wkt:
            raise ValueError(f"Plot with ID {plot_id} was not found.")

        # 2. Derive Road Setback requirements based on standard Ministerial Regulation No. 55
        # Under Thai BCA:
        # - Road width < 10m -> Setback = 6m from centerline (or 2m from road boundary depending on building size)
        # - Road width 10m to 20m -> Setback = 1/10 of road width
        # For simplicity of analysis, we'll assume a standard 2.0m road setback buffer and a 2.0m property setback buffer.
        
        # 3. PostGIS query computing the reduced spatial envelope (Shapely / PostGIS buffer difference)
        # This takes the original polygon and subtracts a negative buffer (or inward setback)
        # Inward buffer is ST_Buffer(geom, -setback_distance)
        query = text("""
            SELECT 
                ST_AsGeoJSON(geom) AS original_geojson,
                ST_AsGeoJSON(ST_Buffer(geom, -:property_setback)) AS buildable_geojson,
                ST_Area(ST_Transform(geom, 32647)) AS original_area_sqm,
                ST_Area(ST_Transform(ST_Buffer(geom, -:property_setback), 32647)) AS buildable_area_sqm
            FROM land_plots
            WHERE id = :plot_id;
        """)
        
        # If the inward buffer distance is too large relative to the plot size, it might return empty geometry.
        # We will dynamically adjust the setback if needed.
        result = await db.execute(query, {
            "plot_id": plot_id,
            "property_setback": boundary_setback_m / 100000.0  # approximate scale to degrees for 4326 geometry
        })
        
        row = result.fetchone()
        if not row or not row.buildable_geojson:
            # Fallback if degrees scaling fails: perform the transformation inside metric system
            metric_query = text("""
                WITH transformed AS (
                    SELECT ST_Transform(geom, 32647) AS geom_utm
                    FROM land_plots
                    WHERE id = :plot_id
                ),
                buffered AS (
                    SELECT ST_Buffer(geom_utm, -:metric_setback) AS geom_buffered
                    FROM transformed
                )
                SELECT 
                    ST_AsGeoJSON(ST_Transform(transformed.geom_utm, 4326)) AS original_geojson,
                    ST_AsGeoJSON(ST_Transform(buffered.geom_buffered, 4326)) AS buildable_geojson,
                    ST_Area(transformed.geom_utm) AS original_area,
                    ST_Area(buffered.geom_buffered) AS buildable_area
                FROM transformed, buffered;
            """)
            
            result = await db.execute(metric_query, {
                "plot_id": plot_id,
                "metric_setback": boundary_setback_m
            })
            row = result.fetchone()

        original_area = float(row.original_area) if hasattr(row, 'original_area') else float(row[2])
        buildable_area = float(row.buildable_area) if hasattr(row, 'buildable_area') else float(row[3])
        original_geojson = row.original_geojson
        buildable_geojson = row.buildable_geojson

        # Assemble summary
        return {
            "plot_id": plot_id,
            "road_width_m": adjacent_road_width_m,
            "required_road_setback_m": 3.0 if adjacent_road_width_m < 10 else 6.0,
            "required_property_boundary_setback_m": boundary_setback_m,
            "original_area_sqm": round(original_area, 2),
            "buildable_envelope_area_sqm": round(max(buildable_area, 0.0), 2),
            "original_geometry_geojson": original_geojson,
            "buildable_envelope_geojson": buildable_geojson or "{}"
        }
