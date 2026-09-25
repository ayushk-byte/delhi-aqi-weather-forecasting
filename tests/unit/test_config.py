"""Unit tests for configuration and domain constants."""

from pathlib import Path

from src.core.config import get_settings
from src.core.constants import (
    CPCB_BREAKPOINTS,
    DELHI_STATIONS,
    PHYSICAL_BOUNDS,
)


def test_get_settings_loads() -> None:
    settings = get_settings()
    assert settings.project_root.exists()
    assert len(settings.horizons_hours) > 0
    assert 24 in settings.horizons_hours
    assert "pm25" in settings.target_pollutants


def test_path_resolution() -> None:
    settings = get_settings()
    resolved = settings.resolve_path("data/raw")
    assert isinstance(resolved, Path)
    assert resolved == settings.project_root / "data" / "raw"


def test_delhi_stations_constants() -> None:
    assert len(DELHI_STATIONS) >= 8
    for st_id, meta in DELHI_STATIONS.items():
        assert "name" in meta
        assert "latitude" in meta
        assert "longitude" in meta
        assert 28.0 <= meta["latitude"] <= 29.5
        assert 76.5 <= meta["longitude"] <= 78.0


def test_cpcb_breakpoints() -> None:
    assert "pm25" in CPCB_BREAKPOINTS
    assert "pm10" in CPCB_BREAKPOINTS
    # Check that PM2.5 covers 0 to 500
    pm25_breaks = CPCB_BREAKPOINTS["pm25"]
    assert pm25_breaks[0][0] == 0.0
    assert pm25_breaks[-1][3] == 500


def test_physical_bounds() -> None:
    assert "pm25" in PHYSICAL_BOUNDS
    min_val, max_val = PHYSICAL_BOUNDS["pm25"]
    assert min_val == 0.0
    assert max_val >= 1000.0
