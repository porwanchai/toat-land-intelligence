import pytest
from app.services.gemini_service import GeminiAIService

@pytest.mark.asyncio
async def test_gemini_rule_based_fallback():
    """
    Verifies that the Gemini service gracefully runs its rule-based mock engine
    as a safe fallback in the absence of API keys.
    """
    service = GeminiAIService()
    # Confirm client is none (since key is empty in testing)
    assert service.client is None

    plot_area = 1500.0
    zones = [
        {
            "zoning_color_code": "yellow",
            "zone_type_name": "Low-Density Residential",
            "far_limit": 2.5,
            "osr_limit": 0.15,
            "coverage_percentage": 100.0,
            "intersection_area_sqm": 1500.0
        }
    ]

    report = await service.analyze_zoning_impact(
        plot_area_sqm=plot_area,
        intersecting_zones=zones,
        proposed_development_type="Commercial Shopping Complex"
    )

    # Verify structured elements
    assert report.max_floor_area_sqm == 1500.0 * 2.5
    assert report.min_open_space_sqm == 1500.0 * 0.15
    assert report.feasibility_score < 80  # Commercial complex inside Yellow zone is highly restricted
    assert report.risk_level in ["high", "critical"]
    assert len(report.construction_constraints) > 0
    assert "ระยะถอยร่น" in report.construction_constraints[0]
