from pydantic import BaseModel, Field
from typing import List

class ZoningImpactRequest(BaseModel):
    plot_id: int = Field(..., description="ID of the land plot to analyze")
    proposed_development_type: str = Field(..., description="Proposed building type (e.g. Hotel, Office, Condominium)")

class QuickSummaryRequest(BaseModel):
    plot_id: int

class ComparePlotsRequest(BaseModel):
    plot_id_1: int
    plot_id_2: int
    proposed_use: str
