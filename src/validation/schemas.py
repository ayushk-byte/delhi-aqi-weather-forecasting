"""Pydantic schemas for tabular records and validation data structures."""

from datetime import datetime

from pydantic import BaseModel, Field


class ObservationRecordSchema(BaseModel):
    """Schema for individual harmonized observation records before feature creation."""

    station_id: str = Field(..., min_length=2, max_length=20)
    timestamp: datetime
    pm25: float | None = Field(None, ge=0.0, le=1500.0)
    pm10: float | None = Field(None, ge=0.0, le=2500.0)
    no2: float | None = Field(None, ge=0.0, le=1000.0)
    so2: float | None = Field(None, ge=0.0, le=1000.0)
    co: float | None = Field(None, ge=0.0, le=100.0)
    o3: float | None = Field(None, ge=0.0, le=1000.0)
    temperature_2m: float | None = Field(None, ge=-10.0, le=60.0)
    relative_humidity_2m: float | None = Field(None, ge=0.0, le=100.0)
    surface_pressure: float | None = Field(None, ge=800.0, le=1150.0)
    wind_speed_10m: float | None = Field(None, ge=0.0, le=60.0)
    wind_direction_10m: float | None = Field(None, ge=0.0, le=360.0)
    boundary_layer_height: float | None = Field(None, ge=10.0, le=7000.0)
    precipitation: float | None = Field(None, ge=0.0, le=500.0)


class ValidationSummary(BaseModel):
    """Data quality check summary metrics."""

    total_rows: int
    cleaned_rows: int
    out_of_bounds_count: int
    stuck_sensor_count: int
    missing_rates: dict[str, float]
    passed: bool
