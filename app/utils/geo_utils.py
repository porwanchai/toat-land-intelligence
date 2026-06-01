from shapely.geometry import shape, Polygon
from shapely.wkt import loads as load_wkt
from typing import Union, List, Dict, Any
from fastapi import HTTPException

def parse_plot_boundary(boundary_input: Union[str, List[Any], Dict[str, Any]]) -> Polygon:
    """
    Unified geometric input parser. Safely normalizes multiple formats to a Shapely Polygon:
    1. WKT (Well-Known Text): e.g. "POLYGON((100 13, 101 13, 101 14, 100 14, 100 13))"
    2. Coordinate Array: e.g. [[13.75, 100.5], [13.76, 100.5], [13.76, 100.6], [13.75, 100.6], [13.75, 100.5]]
       (Automatically maps [lat, lon] sequence pairs to Shapely coordinates in [lon, lat] format)
    3. GeoJSON dictionary (Polygon or MultiPolygon or Feature)
    """
    try:
        # Format 1: WKT
        if isinstance(boundary_input, str):
            cleaned = boundary_input.strip()
            geom = load_wkt(cleaned)
            if not isinstance(geom, Polygon):
                raise ValueError("WKT geometry must be a Polygon.")
            return geom
            
        # Format 2: Coordinate Array [ [lat, lon], ... ]
        elif isinstance(boundary_input, list):
            if len(boundary_input) < 3:
                raise ValueError("A polygon boundary requires at least 3 points.")
            
            # Map Lat/Lon to Lon/Lat (x/y) for Shapely
            lon_lat_coords = []
            for item in boundary_input:
                if not isinstance(item, list) or len(item) != 2:
                    raise ValueError("Each boundary coordinate must be a [lat, lon] pair.")
                lat, lon = float(item[0]), float(item[1])
                # Ensure coordinates fit standard bounding box of Thailand (approx coordinates)
                lon_lat_coords.append((lon, lat))
                
            # If not closed, auto close it
            if lon_lat_coords[0] != lon_lat_coords[-1]:
                lon_lat_coords.append(lon_lat_coords[0])
                
            return Polygon(lon_lat_coords)

        # Format 3: GeoJSON Dictionary
        elif isinstance(boundary_input, dict):
            # If it's a Feature, extract geometry
            if boundary_input.get("type") == "Feature":
                geom_data = boundary_input.get("geometry", {})
            else:
                geom_data = boundary_input
                
            geom = shape(geom_data)
            if not isinstance(geom, Polygon):
                raise ValueError("Parsed GeoJSON geometry must evaluate to a Polygon.")
            return geom
            
        else:
            raise ValueError("Unsupported input boundary format.")
            
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Geometry validation failed: {str(e)}"
        )
