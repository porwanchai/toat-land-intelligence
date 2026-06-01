import pytest
from app.services.far_osr_calculator import ZoningCalculatorService

def test_single_zone_calculation():
    """
    Tests mathematical capacity projections on a simple single zone plot.
    """
    plot_area = 1000.0  # sqm
    intersecting_zones = [
        {
            "zoning_color_code": "red",
            "zone_type_name": "Commercial Zone",
            "far_limit": 8.0,
            "osr_limit": 0.05,
            "coverage_percentage": 100.0,
            "intersection_area_sqm": 1000.0
        }
    ]

    results = ZoningCalculatorService.calculate_development_capacity(plot_area, intersecting_zones)
    
    assert results["max_gross_floor_area_sqm"] == 8000.0
    assert results["min_open_space_area_sqm"] == 50.0
    assert results["max_building_footprint_sqm"] == 950.0
    assert results["estimated_maximum_stories"] == 8

def test_split_zone_calculation():
    """
    Tests capacity projections when a plot is split across two administrative zones (50/50 split).
    """
    plot_area = 2000.0  # sqm
    intersecting_zones = [
        {
            "zoning_color_code": "orange",
            "zone_type_name": "Residential Zone",
            "far_limit": 4.0,
            "osr_limit": 0.10,
            "coverage_percentage": 50.0,
            "intersection_area_sqm": 1000.0
        },
        {
            "zoning_color_code": "yellow",
            "zone_type_name": "Low-Density Residential",
            "far_limit": 2.0,
            "osr_limit": 0.20,
            "coverage_percentage": 50.0,
            "intersection_area_sqm": 1000.0
        }
    ]

    results = ZoningCalculatorService.calculate_development_capacity(plot_area, intersecting_zones)
    
    # Expected weighted calculations
    # Zone 1 Area = 1000, FAR GFA = 4000, OSA = 100
    # Zone 2 Area = 1000, FAR GFA = 2000, OSA = 200
    # Total GFA = 6000, Total OSA = 300
    assert results["max_gross_floor_area_sqm"] == 6000.0
    assert results["min_open_space_area_sqm"] == 300.0
    assert results["max_building_footprint_sqm"] == 1700.0
    assert results["weighted_far_limit"] == 3.0
    assert results["weighted_osr_limit"] == 0.15
