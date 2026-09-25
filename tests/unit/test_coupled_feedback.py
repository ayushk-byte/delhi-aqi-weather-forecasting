"""Unit tests for the coupled atmospheric-chemical feedback engine and 72h forecaster."""

import pytest
from src.modeling.coupled_feedback import AtmosphericFeedbackEngine
from src.preprocessing.aqi_calculator import calculate_aqi, calculate_sub_index, get_aqi_category


def test_inversion_index_severe():
    """Test that low PBL height (<200m) and calm winds trigger severe inversion cap."""
    result = AtmosphericFeedbackEngine.calculate_inversion_index(
        pbl_height=120.0,
        wind_speed=0.8,
        temperature=14.0,
        relative_humidity=85.0,
    )
    assert result["inversion_index"] >= 70.0
    assert result["category"] == "Severe Inversion Cap"
    assert result["severity"] == "critical"


def test_inversion_index_well_mixed():
    """Test that high daytime PBL height (>1500m) and strong winds produce a well-mixed atmosphere."""
    result = AtmosphericFeedbackEngine.calculate_inversion_index(
        pbl_height=1600.0,
        wind_speed=5.5,
        temperature=32.0,
        relative_humidity=40.0,
    )
    assert result["inversion_index"] < 40.0
    assert result["category"] == "Well-Mixed Atmosphere"


def test_stubble_plume_nw_corridor():
    """Test that North-Westerly winds (315 deg) at 3.5 m/s trigger high regional stubble influx."""
    result = AtmosphericFeedbackEngine.calculate_stubble_plume_advection(
        wind_direction_deg=315.0,
        wind_speed_ms=3.5,
        inversion_index=75.0,
    )
    assert result["plume_index"] >= 65.0
    assert result["risk"] == "high"


def test_stubble_plume_easterly():
    """Test that Easterly winds (90 deg) do not trigger NW agricultural corridor smoke influx."""
    result = AtmosphericFeedbackEngine.calculate_stubble_plume_advection(
        wind_direction_deg=90.0,
        wind_speed_ms=4.0,
        inversion_index=30.0,
    )
    assert result["plume_index"] < 20.0
    assert result["risk"] == "low"


def test_aerosol_radiation_feedback():
    """Test solar dimming and boundary layer suppression from dense PM2.5 loading."""
    result = AtmosphericFeedbackEngine.simulate_aerosol_radiation_feedback(
        pm25_concentration=350.0,
        base_pbl_height=800.0,
        temperature_2m=28.0,
    )
    assert result["temperature_depression_deg_c"] > 1.0
    assert result["pbl_suppression_pct"] > 15.0
    assert result["effective_pbl_height_m"] < 800.0
    assert result["active_feedback"] is True


def test_cpcb_ozone_subindex():
    """Test that ground-level ozone sub-index follows CPCB breakpoints."""
    sub_50 = calculate_sub_index("o3", 40.0)
    assert sub_50 is not None and sub_50 <= 50.0

    sub_poor = calculate_sub_index("o3", 190.0)
    assert sub_poor is not None and 200.0 <= sub_poor <= 300.0

    cat = get_aqi_category(sub_poor)
    assert cat == "Poor"
