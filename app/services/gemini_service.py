import logging
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

class ZoningFeasibilityReport(BaseModel):
    max_floor_area_sqm: float = Field(..., description="Maximum allowed gross floor area in sqm under FAR constraints")
    min_open_space_sqm: float = Field(..., description="Minimum required open space area in sqm under OSR constraints")
    feasibility_score: int = Field(..., description="Feasibility score from 0 (impossible) to 100 (excellent)")
    risk_level: str = Field(..., description="Risk tier: 'low', 'medium', 'high', or 'critical'")
    recommended_development_types: List[str] = Field(..., description="Viable building categories recommended for this zone")
    construction_constraints: List[str] = Field(..., description="Specific structural, height, or setback restrictions")
    thai_regulation_notes: str = Field(..., description="Specific references to Thai Ministerial Zoning Regulations or Building Control Act")
    executive_summary: str = Field(..., description="Natural language summary of findings and strategic recommendations")

class GeminiAIService:
    def __init__(self):
        # Instantiate the new google-genai Client
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            logger.warning("GEMINI_API_KEY not configured. AI services will run in Mock mode.")
            self.client = None

    async def analyze_zoning_impact(
        self,
        plot_area_sqm: float,
        intersecting_zones: List[Dict[str, Any]],
        proposed_development_type: str
    ) -> ZoningFeasibilityReport:
        """
        Synthesizes spatial audit data, FAR/OSR constraints, and user's development requirements.
        Invokes Google Gemini API to generate structured regulatory zoning feasibility reports.
        """
        # If API key is missing, return fallback mock data to keep application robust
        if not self.client:
            return self._generate_mock_report(plot_area_sqm, intersecting_zones, proposed_development_type)

        # 1. Format zoning parameters for prompt context
        zones_summary = []
        for zone in intersecting_zones:
            zones_summary.append(
                f"- Zone: {zone['zone_type_name']} (Color Code: {zone['zoning_color_code']})\n"
                f"  Coverage: {zone['coverage_percentage']}% ({zone['intersection_area_sqm']:.2f} sqm)\n"
                f"  FAR Limit: {zone.get('far_limit') or 'No Limit'}\n"
                f"  OSR Limit: {zone.get('osr_limit') or 'No Limit'}\n"
                f"  Restrictions: {zone.get('construction_restrictions_text') or 'None listed'}"
            )
        zones_context = "\n\n".join(zones_summary)

        # 2. Build precision prompt
        prompt = f"""
You are an expert Thai urban planning consultant and land development advisor.
Analyze the development feasibility of the following proposed project under the Thai Building Control Act (BCA) and regional Comprehensive Zoning Codes (ผังเมืองรวม).

### Proposed Project Parameters:
- Total Land Plot Area: {plot_area_sqm:.2f} sqm (approx. {plot_area_sqm / 4.0:.2f} Square Wah - ตารางวา)
- Proposed Building / Development Category: {proposed_development_type}

### Intersecting Zoning Layers from GIS Spatial Audit:
{zones_context}

### Analysis Guidelines & Mandatory Compliance Rules:
1. Max Buildable Floor Area (Gross Floor Area):
   Calculate aggregate FAR capacity: Sum of (Zone Area * FAR Limit). If no limit, assume standard BCA defaults (usually 10.0 or 1000% for high density, or warn).
2. Min Required Open Space (OSR):
   Calculate minimum open space required: Sum of (Zone Area * OSR Limit).
3. Analyze Zoning Restrictions:
   Check the construction_restrictions_text specifically against the proposed use ({proposed_development_type}). Note any prohibitions.
4. Strategic Feasibility Score & Risk Level:
   Deduce score (0-100) based on how restrictive the zone is to the proposed development. High mismatch = high risk.
5. Identify Thai Regulatory Nuances:
   Reference corresponding regulatory boards (e.g. EIA thresholds for residential projects exceeding 79 units or hotels with 80+ rooms, height caps near historical sites, or Bangkok comprehensive plan details).

Provide your final analysis in Thai/English bilingual format where applicable.
"""

        try:
            # Call the new gemini SDK endpoint with response_schema enforcement
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ZoningFeasibilityReport,
                    temperature=0.2, # low temperature for strict factual alignment
                )
            )
            
            # Parse the structured response
            report = ZoningFeasibilityReport.model_validate_json(response.text)
            return report
            
        except Exception as e:
            logger.exception("Failed to query Gemini AI API. Falling back to rule-based parser.")
            return self._generate_mock_report(plot_area_sqm, intersecting_zones, proposed_development_type, error=str(e))

    def _generate_mock_report(
        self, 
        plot_area_sqm: float, 
        intersecting_zones: List[Dict[str, Any]], 
        proposed_use: str,
        error: str = None
    ) -> ZoningFeasibilityReport:
        """
        Highly robust rule-based mock report engine used as fallback or when API Keys are omitted.
        """
        # Calculate rule-based capacities as backup
        primary_zone = intersecting_zones[0] if intersecting_zones else {}
        far = primary_zone.get("far_limit") or 3.0
        osr = primary_zone.get("osr_limit") or 0.10
        
        max_floor_area = plot_area_sqm * far
        min_open_space = plot_area_sqm * osr
        
        # Simple feasibility logic
        feasibility = 85
        risk = "low"
        restrictions = ["ระยะถอยร่นตามพระราชบัญญัติควบคุมอาคาร", "ข้อจำกัดความสูงตามขนาดความกว้างถนน"]
        
        proposed_lower = proposed_use.lower()
        if "hotel" in proposed_lower or "commercial" in proposed_lower:
            if "yellow" in primary_zone.get("zoning_color_code", "").lower() or "orange" in primary_zone.get("zoning_color_code", "").lower():
                feasibility = 50
                risk = "high"
                restrictions.append("ข้อจำกัดการก่อสร้างอาคารพาณิชย์ขนาดใหญ่ในพื้นที่อยู่อาศัยหนาแน่นน้อย/ปานกลาง")
        
        summary = (
            f"การประเมินเบื้องต้นสำหรับโครงการประเภท {proposed_use} บนที่ดินขนาด {plot_area_sqm:.2f} ตร.ม. "
            f"ในพื้นที่โซนผังสี {primary_zone.get('zoning_color_code', 'N/A')} ({primary_zone.get('zone_type_name', 'N/A')}). "
            f"มีพื้นที่ก่อสร้างสูงสุดที่อนุญาต (FAR) ประมาณ {max_floor_area:.2f} ตร.ม. และพื้นที่ว่างทางกฎหมาย (OSR) ไม่น้อยกว่า {min_open_space:.2f} ตร.ม."
        )
        
        if error:
            summary += f"\n\n[System Alert: Gemini API unavailable - generated using spatial rules. Details: {error}]"

        return ZoningFeasibilityReport(
            max_floor_area_sqm=max_floor_area,
            min_open_space_sqm=min_open_space,
            feasibility_score=feasibility,
            risk_level=risk,
            recommended_development_types=[proposed_use, "Residential Townhouse", "Low-rise Condominium"],
            construction_constraints=restrictions,
            thai_regulation_notes="อ้างอิงพระราชบัญญัติควบคุมอาคาร พ.ศ. 2522 และผังเมืองรวมฉบับปัจจุบัน",
            executive_summary=summary
        )
