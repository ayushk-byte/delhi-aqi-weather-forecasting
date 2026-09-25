"""Abstract Base Classes and Data Models for Ingestion Providers."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AQIObservation(BaseModel):
    """Standardized schema for air quality observations across all stations and providers."""

    station_id: str = Field(..., description="Internal normalized station identifier (e.g. DL001)")
    timestamp: datetime = Field(..., description="Observation timestamp in UTC")
    pm25: float | None = Field(None, description="PM2.5 concentration in ug/m3")
    pm10: float | None = Field(None, description="PM10 concentration in ug/m3")
    no2: float | None = Field(None, description="NO2 concentration in ug/m3")
    so2: float | None = Field(None, description="SO2 concentration in ug/m3")
    co: float | None = Field(None, description="CO concentration in mg/m3")
    o3: float | None = Field(None, description="O3 concentration in ug/m3")
    aqi: float | None = Field(None, description="Reported AQI index if provided by station")
    provider: str = Field(..., description="Name of the ingestion provider")
    raw_payload: dict[str, Any] | None = Field(
        default=None, description="Original API response fragment"
    )


class WeatherObservation(BaseModel):
    """Standardized schema for historical or current meteorological observations."""

    latitude: float
    longitude: float
    timestamp: datetime = Field(..., description="Observation timestamp in UTC")
    temperature_2m: float | None = Field(None, description="Ambient temperature at 2m (deg C)")
    relative_humidity_2m: float | None = Field(None, description="Relative humidity at 2m (%)")
    dew_point_2m: float | None = Field(None, description="Dew point temperature at 2m (deg C)")
    surface_pressure: float | None = Field(None, description="Surface atmospheric pressure (hPa)")
    wind_speed_10m: float | None = Field(None, description="Wind speed at 10m (m/s)")
    wind_direction_10m: float | None = Field(None, description="Wind direction in degrees (0-360)")
    wind_gusts_10m: float | None = Field(None, description="Wind gusts at 10m (m/s)")
    boundary_layer_height: float | None = Field(
        None, description="Planetary boundary layer height (m)"
    )
    precipitation: float | None = Field(None, description="Precipitation rate (mm)")
    provider: str = Field(..., description="Name of the weather provider")


class WeatherForecast(WeatherObservation):
    """Standardized schema for external NWP / numerical weather forecasts."""

    forecast_run_time: datetime = Field(
        ..., description="Timestamp when the forecast model was initialized"
    )
    forecast_horizon_hours: int = Field(
        ..., description="Forecast horizon offset in hours (e.g. 6, 24, 48)"
    )


class BaseAQIProvider(ABC):
    """Abstract interface for all Air Quality observation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier name for this provider."""

    @abstractmethod
    def fetch_latest_observations(
        self, station_ids: list[str] | None = None
    ) -> list[AQIObservation]:
        """Fetch real-time observations for given stations or all monitored Delhi stations.

        Args:
            station_ids: Optional list of internal station IDs. If None, fetch for all stations.

        Returns:
            List of standardized AQIObservation items.
        """

    @abstractmethod
    def fetch_historical_observations(
        self,
        start_date: datetime,
        end_date: datetime,
        station_ids: list[str] | None = None,
    ) -> list[AQIObservation]:
        """Fetch historical records between start_date and end_date."""


class BaseWeatherProvider(ABC):
    """Abstract interface for all meteorological observation and NWP forecast providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier name for this provider."""

    @abstractmethod
    def fetch_current_weather(self, latitude: float, longitude: float) -> WeatherObservation:
        """Fetch current weather observations for a coordinate pair."""

    @abstractmethod
    def fetch_historical_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
    ) -> list[WeatherObservation]:
        """Fetch historical meteorological time series for a coordinate pair."""

    @abstractmethod
    def fetch_forecast_weather(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 3,
    ) -> list[WeatherForecast]:
        """Fetch upcoming weather forecast for a coordinate pair."""
