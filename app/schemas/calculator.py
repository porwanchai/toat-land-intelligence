from pydantic import BaseModel, Field

class CalculatorRequest(BaseModel):
    plot_id: int = Field(..., description="ID of the land plot to analyze")

class CalculatorResponse(BaseModel):
    total_plot_area_sqm: float
    weighted_far_limit: float
    weighted_osr_limit: float
    max_gross_floor_area_sqm: float
    min_open_space_area_sqm: float
    max_building_footprint_sqm: float
    building_coverage_ratio_percentage: float
    estimated_maximum_stories: int
