from pydantic import BaseModel, Field
from typing import Optional, Union, List, Dict, Any
from datetime import datetime

class LandPlotCreate(BaseModel):
    plot_name: Optional[str] = Field(None, description="Descriptive name of the land plot")
    address_text: Optional[str] = Field(None, description="Land plot physical address details")
    
    # Boundary accepts multiple formats (WKT, coordinate arrays or GeoJSON geometries)
    boundary: Union[str, List[Any], Dict[str, Any]] = Field(
        ..., 
        description="Plot boundary. Accepts WKT string, GeoJSON object, or array of [lat, lon] coordinate pairs."
    )

class LandPlotResponse(BaseModel):
    id: int
    plot_name: Optional[str] = None
    total_area_sqm: float
    address_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
