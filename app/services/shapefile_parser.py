import os
import logging
import geopandas as gpd
from pathlib import Path
from typing import List, Dict, Any
from shapely.geometry import Polygon, MultiPolygon
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import from_shape

from app.models.urban_zoning import UrbanZoningLayer
from app.utils.file_utils import safe_extract_zip

logger = logging.getLogger(__name__)

class ShapefileParserService:
    @staticmethod
    def parse_zip_to_gdf(zip_path: Path) -> gpd.GeoDataFrame:
        """
        Unzips files and loads them into a GeoPandas GeoDataFrame.
        Automatically detects shapefiles (.shp) or GeoJSON files.
        """
        import tempfile
        # Create temp dir for extraction
        temp_dir = Path(tempfile.mkdtemp(prefix="toat_shape_"))
        logger.info(f"Extracting zip archive {zip_path.name} to {temp_dir}")
        
        safe_extract_zip(zip_path, temp_dir)
        
        # 1. Search for shapefiles
        shp_files = list(temp_dir.rglob("*.shp"))
        if shp_files:
            logger.info(f"Discovered Shapefile: {shp_files[0]}")
            gdf = gpd.read_file(shp_files[0])
            return gdf
            
        # 2. Search for GeoJSON files
        geojson_files = list(temp_dir.rglob("*.geojson")) + list(temp_dir.rglob("*.json"))
        if geojson_files:
            logger.info(f"Discovered GeoJSON: {geojson_files[0]}")
            gdf = gpd.read_file(geojson_files[0])
            return gdf
            
        raise ValueError("ZIP archive contains no recognizable Shapefile (.shp) or GeoJSON data.")

    @classmethod
    async def process_and_import(
        cls, 
        zip_path: Path, 
        db: AsyncSession, 
        published_fiscal_year: int
    ) -> int:
        """
        Ingestion pipeline:
        1. Extract and load to GeoDataFrame
        2. Validate/project CRS: Target local UTM 32647 (Zone 47N, Thailand standard) for analytical safety,
           then convert geometry properties back to EPSG:4326 for standard DB multi-polygon storage.
        3. Parse metadata: FAR, OSR, zoning color codes, zoning restrictions text
        4. Bulk insert into database
        """
        gdf = cls.parse_zip_to_gdf(zip_path)
        logger.info(f"Successfully loaded {len(gdf)} rows from spatial dataset.")

        # Ensure active coordinate reference system exists
        if gdf.crs is None:
            logger.warning("No projection (CRS) found in source. Assuming default WGS84 (EPSG:4326).")
            gdf = gdf.set_crs(epsg=4326)

        # Reproject to standard Thailand UTM Zone 47N (EPSG:32647) to standardise metric integrity
        gdf_utm = gdf.to_crs(epsg=32647)
        logger.info(f"Reprojected input dataset CRS from {gdf.crs} to standard EPSG:32647.")

        # Re-project back to WGS84 for database storage (EPSG:4326)
        gdf_wgs84 = gdf_utm.to_crs(epsg=4326)

        records_inserted = 0
        
        for idx, row in gdf_wgs84.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue

            # Ensure geometry evaluates to a MultiPolygon
            if isinstance(geom, Polygon):
                multipoly = MultiPolygon([geom])
            elif isinstance(geom, MultiPolygon):
                multipoly = geom
            else:
                logger.warning(f"Unsupported geometry type at row {idx}: {geom.geom_type}. Skipping.")
                continue

            # Mapping columns - matching official attributes in Shapefiles dynamically (case insensitive)
            # Looks for common color naming standard variations: zoning_color, color_code, etc.
            properties = row.to_dict()
            
            zoning_color_code = cls._find_key(properties, ["color_code", "zoning_color", "color", "colour", "zone_color"], "UNKNOWN")
            zone_type_name = cls._find_key(properties, ["zone_type_name", "zone_name", "zone_type", "type_name", "title"], "General Zone")
            
            # Numeric limitations (FAR/OSR)
            far_val = cls._find_float(properties, ["far_limit", "far", "floor_area_ratio"])
            osr_val = cls._find_float(properties, ["osr_limit", "osr", "open_space_ratio"])
            
            restrictions = cls._find_key(properties, ["construction_restrictions_text", "restrictions", "notes", "law_text"], None)

            # Build record with geometry mapped to standard GeoAlchemy shape
            layer_record = UrbanZoningLayer(
                zoning_color_code=zoning_color_code,
                zone_type_name=zone_type_name,
                far_limit=far_val,
                osr_limit=osr_val,
                construction_restrictions_text=restrictions,
                published_fiscal_year=published_fiscal_year,
                geom=from_shape(multipoly, srid=4326),
                source_filename=zip_path.name,
                is_active=True,
                version_number=1
            )
            
            db.add(layer_record)
            records_inserted += 1

        await db.commit()
        logger.info(f"Ingested {records_inserted} zoning polygons successfully.")
        return records_inserted

    @staticmethod
    def _find_key(properties: Dict[str, Any], candidates: List[str], default: Any) -> Any:
        for key, value in properties.items():
            if key.lower() in candidates:
                return str(value) if value is not None else default
        return default

    @staticmethod
    def _find_float(properties: Dict[str, Any], candidates: List[str]) -> Optional[float]:
        for key, value in properties.items():
            if key.lower() in candidates:
                try:
                    return float(value) if value is not None else None
                except ValueError:
                    return None
        return None
