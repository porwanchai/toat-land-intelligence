import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ZoningCalculatorService:
    @staticmethod
    def calculate_development_capacity(
        plot_area_sqm: float,
        intersecting_zones: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Computes the theoretical maximum buildable parameters based on FAR & OSR variables.
        - Calculates total allowable Gross Floor Area (GFA) weighted across overlapping zones.
        - Calculates total mandatory Open Space Area (OSA).
        - Computes theoretical building footprint limits.
        - Projects estimate building stories based on typical construction defaults.
        """
        total_gfa_allowed = 0.0
        total_osa_required = 0.0
        weighted_far = 0.0
        weighted_osr = 0.0
        
        total_coverage_accounted = 0.0

        for zone in intersecting_zones:
            coverage_pct = zone.get("coverage_percentage", 0.0)
            zone_area = (coverage_pct / 100.0) * plot_area_sqm
            
            far = zone.get("far_limit") or 0.0
            osr = zone.get("osr_limit") or 0.0

            # Allowable Floor Area inside this slice
            total_gfa_allowed += zone_area * far
            total_osa_required += zone_area * osr
            
            weighted_far += far * (coverage_pct / 100.0)
            weighted_osr += osr * (coverage_pct / 100.0)
            total_coverage_accounted += coverage_pct

        # Building footprint is constrained by Open Space requirements: Max Footprint = Plot Area - OSA
        max_footprint = plot_area_sqm - total_osa_required
        if max_footprint < 0:
            max_footprint = 0.0

        # Building Coverage Ratio
        bcr = (max_footprint / plot_area_sqm) * 100.0 if plot_area_sqm > 0 else 0.0

        # Estimated allowable stories (GFA / Footprint)
        estimated_stories = 0
        if max_footprint > 0:
            estimated_stories = int(total_gfa_allowed / max_footprint)

        return {
            "total_plot_area_sqm": plot_area_sqm,
            "weighted_far_limit": round(weighted_far, 2),
            "weighted_osr_limit": round(weighted_osr, 2),
            "max_gross_floor_area_sqm": round(total_gfa_allowed, 2),
            "min_open_space_area_sqm": round(total_osa_required, 2),
            "max_building_footprint_sqm": round(max_footprint, 2),
            "building_coverage_ratio_percentage": round(bcr, 2),
            "estimated_maximum_stories": estimated_stories
        }
