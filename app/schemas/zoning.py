from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UrbanZoningLayerBase(BaseModel):
    zoning_color_code: str = Field(..., description="Official zoning color code (e.g. #FF0000, #E6A23C)")
    zone_type_name: str = Field(..., description="Official zone description name (e.g. residential, commercial)")
    far_limit: Optional[float] = Field(None, description="Floor Area Ratio limit")
    osr_limit: Optional[float] = Field(None, description="Open Space Ratio limit")
    construction_restrictions_text: Optional[str] = Field(None, description="Official restriction text details")
    published_fiscal_year: Optional[int] = Field(None, description="Fiscal year of publication")

class UrbanZoningLayerCreate(UrbanZoningLayerBase):
    pass

class UrbanZoningLayerResponse(UrbanZoningLayerBase):
    id: int
    uploaded_at: datetime
    is_active: bool
    version_number: int

    model_config = {
        "from_attributes": True
    }

class UploadStatusResponse(BaseModel):
    job_id: str
    status: str  # "queued", "processing", "completed", "failed"
    progress: Optional[float] = None
    imported_polygons_count: Optional[int] = None
    error: Optional[str] = None
