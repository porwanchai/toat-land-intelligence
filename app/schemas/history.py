from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class HistoryTimelineResponse(BaseModel):
    history_id: int
    zoning_color_code: str
    change_type: str
    old_far: Optional[float] = None
    new_far: Optional[float] = None
    old_osr: Optional[float] = None
    new_osr: Optional[float] = None
    old_zone_type: Optional[str] = None
    new_zone_type: Optional[str] = None
    changed_at: str
    fiscal_year: int
    change_notes: Optional[str] = None
