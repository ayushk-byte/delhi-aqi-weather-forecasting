"""Concrete Weather Provider implementation using the Open-Meteo API."""

from datetime import datetime, timezone
from typing import Any

import httpx

from src.core.exceptions import ProviderUnavailableError
from src.core.logging import get_logger
from src.ingestion.base import BaseWeatherProvider, WeatherForecast, WeatherObservation

logger = get_logger(__name__)


class OpenMeteoProvider(BaseWeatherProvider):
    """Fetches high-resolution weather observations and NWP forecasts via Open-Meteo."""

    def __init__(
        self,
        forecast_url: str = "https://api.open-meteo.com/v1/forecast",
        historical_url: str = "https://archive-api.open-meteo.com/v1/archive",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.forecast_url = forecast_url
        self.historical_url = historical_url
        self.timeout_seconds = timeout_seconds
        self.hourly_params = [
            "temperature_2m",
            "relative_humidity_2m",
            "dew_point_2m",
            "surface_pressure",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "boundary_layer_height",
            "precipitation",
        ]

    @property
    def provider_name(self) -> str:
        return "open_meteo"

    def fetch_current_weather(self, latitude: float, longitude: float) -> WeatherObservation:
        """Fetch current weather conditions by requesting recent hourly values."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
                "precipitation",
            ],
            "wind_speed_unit": "ms",
            "timezone": "UTC",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.get(self.forecast_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.error(f"Failed to fetch current weather from Open-Meteo: {exc}")
            raise ProviderUnavailableError(f"Open-Meteo current weather failed: {exc}") from exc

        curr = data.get("current", {})
        ts_str = curr.get("time")
        if not ts_str:
            raise ProviderUnavailableError(
                "Open-Meteo response did not include an observation time"
            )
        if not any(
            curr.get(key) is not None
            for key in (
                "temperature_2m",
                "relative_humidity_2m",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
                "precipitation",
            )
        ):
            raise ProviderUnavailableError("Open-Meteo response contains no current weather values")
        timestamp = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)

        return WeatherObservation(
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
            temperature_2m=curr.get("temperature_2m"),
            relative_humidity_2m=curr.get("relative_humidity_2m"),
            dew_point_2m=None,
            surface_pressure=curr.get("surface_pressure"),
            wind_speed_10m=curr.get("wind_speed_10m"),
            wind_direction_10m=curr.get("wind_direction_10m"),
            wind_gusts_10m=None,
            boundary_layer_height=None,
            precipitation=curr.get("precipitation"),
            provider=self.provider_name,
        )

    def fetch_historical_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
    ) -> list[WeatherObservation]:
        """Fetch historical meteorological time series from Open-Meteo archive."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "hourly": ",".join(self.hourly_params),
            "wind_speed_unit": "ms",
            "timezone": "UTC",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.get(self.historical_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.error(f"Failed to fetch historical weather from Open-Meteo: {exc}")
            raise ProviderUnavailableError(f"Open-Meteo historical failed: {exc}") from exc

        return self._parse_hourly_observations(data, latitude, longitude)

    def fetch_forecast_weather(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 3,
    ) -> list[WeatherForecast]:
        """Fetch future NWP hourly forecasts from Open-Meteo."""
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(self.hourly_params),
            "wind_speed_unit": "ms",
            "forecast_days": min(forecast_days, 16),
            "timezone": "UTC",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.get(self.forecast_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.error(f"Failed to fetch forecast from Open-Meteo: {exc}")
            raise ProviderUnavailableError(f"Open-Meteo forecast failed: {exc}") from exc

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        forecasts: list[WeatherForecast] = []

        for i, time_str in enumerate(times):
            dt = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
            if dt <= now:
                continue

            horizon_hours = int((dt - now).total_seconds() // 3600)
            forecasts.append(
                WeatherForecast(
                    latitude=latitude,
                    longitude=longitude,
                    timestamp=dt,
                    temperature_2m=self._safe_get(hourly, "temperature_2m", i),
                    relative_humidity_2m=self._safe_get(hourly, "relative_humidity_2m", i),
                    dew_point_2m=self._safe_get(hourly, "dew_point_2m", i),
                    surface_pressure=self._safe_get(hourly, "surface_pressure", i),
                    wind_speed_10m=self._safe_get(hourly, "wind_speed_10m", i),
                    wind_direction_10m=self._safe_get(hourly, "wind_direction_10m", i),
                    wind_gusts_10m=self._safe_get(hourly, "wind_gusts_10m", i),
                    boundary_layer_height=self._safe_get(hourly, "boundary_layer_height", i),
                    precipitation=self._safe_get(hourly, "precipitation", i),
                    provider=self.provider_name,
                    forecast_run_time=now,
                    forecast_horizon_hours=horizon_hours,
                )
            )

        return forecasts

    def _parse_hourly_observations(
        self, data: dict[str, Any], latitude: float, longitude: float
    ) -> list[WeatherObservation]:
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        observations: list[WeatherObservation] = []

        for i, time_str in enumerate(times):
            dt = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
            observations.append(
                WeatherObservation(
                    latitude=latitude,
                    longitude=longitude,
                    timestamp=dt,
                    temperature_2m=self._safe_get(hourly, "temperature_2m", i),
                    relative_humidity_2m=self._safe_get(hourly, "relative_humidity_2m", i),
                    dew_point_2m=self._safe_get(hourly, "dew_point_2m", i),
                    surface_pressure=self._safe_get(hourly, "surface_pressure", i),
                    wind_speed_10m=self._safe_get(hourly, "wind_speed_10m", i),
                    wind_direction_10m=self._safe_get(hourly, "wind_direction_10m", i),
                    wind_gusts_10m=self._safe_get(hourly, "wind_gusts_10m", i),
                    boundary_layer_height=self._safe_get(hourly, "boundary_layer_height", i),
                    precipitation=self._safe_get(hourly, "precipitation", i),
                    provider=self.provider_name,
                )
            )
        return observations

    @staticmethod
    def _safe_get(data: dict[str, list[Any]], key: str, index: int) -> float | None:
        series = data.get(key, [])
        if index < len(series) and series[index] is not None:
            return float(series[index])
        return None
