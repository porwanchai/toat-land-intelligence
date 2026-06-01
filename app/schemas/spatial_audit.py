from pydantic import BaseModel, Field
from typing import List, Optional

class IntersectingZoneDetail(BaseModel):
    layer_id: int
    zoning_color_code: str
    zone_type_name: str
    far_limit: Optional[float] = None
    osr_limit: Optional[float] = None
    construction_restrictions_text: Optional[str] = None
    published_fiscal_year: Optional[int] = None
    intersection_area_sqm: float
    coverage_percentage: float
    zone_geojson: str = Field(..., description="Zoning boundary geometry as a GeoJSON string")
    intersection_geojson: str = Field(..., description="Intersecting portion geometry as a GeoJSON string")

class SpatialAuditResponse(BaseModel):
    plot_id: int
    total_plot_area_sqm: float
    intersecting_zones: List[IntersectingZoneDetail]
    execution_time_ms: int
