from pydantic import BaseModel, Field
from typing import Optional

class SetbackRequest(BaseModel):
    plot_id: int = Field(..., description="ID of the land plot to analyze")
    adjacent_road_width_m: Optional[float] = Field(6.0, description="Width of the adjacent public road in meters")
    boundary_setback_m: Optional[float] = Field(2.0, description="Standard property boundary buffer in meters")

class SetbackResponse(BaseModel):
    plot_id: int
    road_width_m: float
    required_road_setback_m: float
    required_property_boundary_setback_m: float
    original_area_sqm: float
    buildable_envelope_area_sqm: float
    original_geometry_geojson: str
    buildable_envelope_geojson: str
