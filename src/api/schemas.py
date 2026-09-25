"""Pydantic schemas for REST API request and response validation."""

from datetime import datetime

from pydantic import BaseModel, Field


class HorizonForecastSchema(BaseModel):
    horizon_hours: int = Field(..., description="Horizon offset in hours (e.g. 6, 12, 24, 48)")
    forecast_timestamp: datetime
    predicted_pm25: float = Field(..., description="Predicted PM2.5 in ug/m3")
    predicted_pm10: float = Field(..., description="Predicted PM10 in ug/m3")
    predicted_aqi: int = Field(..., description="Calculated CPCB IND-AQI index")
    aqi_category: str = Field(..., description="CPCB qualitative descriptor (Good..Severe)")
    dominant_pollutant: str = "pm25"


class StationForecastResponse(BaseModel):
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    horizons: list[HorizonForecastSchema]


class CitySummarySchema(BaseModel):
    horizon_hours: int
    forecast_timestamp: datetime
    city_mean_pm25: float
    city_max_pm25: float
    city_min_pm25: float
    city_mean_aqi: int
    aqi_category: str


class ForecastResponse(BaseModel):
    status: str
    generated_at: datetime
    latest_observation_timestamp: datetime
    model_name: str
    target_pollutant: str
    city_summary: list[CitySummarySchema]
    stations: list[StationForecastResponse]


class StationMetadataSchema(BaseModel):
    station_id: str
    name: str
    latitude: float
    longitude: float
    cpcb_id: str | None = None
    zone: str | None = None


class CurrentObservationSchema(BaseModel):
    station_id: str
    station_name: str
    timestamp: datetime
    pm25: float | None = None
    pm10: float | None = None
    temperature_2m: float | None = None
    relative_humidity_2m: float | None = None
    wind_speed_10m: float | None = None
    wind_direction_10m: float | None = None
    boundary_layer_height: float | None = None
    cpcb_aqi: int | None = None
    aqi_category: str | None = None


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    environment: str
    version: str
    champion_models: dict[str, str]
