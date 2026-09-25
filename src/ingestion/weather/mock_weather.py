"""Mock weather provider generating realistic atmospheric features including boundary layer collapse."""

import math
from datetime import datetime, timedelta, timezone

from src.ingestion.base import BaseWeatherProvider, WeatherForecast, WeatherObservation


class MockWeatherProvider(BaseWeatherProvider):
    """Generates synthetic weather observations and forecasts for Delhi NCR coordinates."""

    def __init__(self, base_temp: float = 24.0) -> None:
        self._base_temp = base_temp

    @property
    def provider_name(self) -> str:
        return "mock_weather"

    def _generate_point(
        self, lat: float, lon: float, dt: datetime
    ) -> tuple[float, float, float, float, float, float, float, float, float]:
        hour = dt.hour + dt.minute / 60.0
        # Temperature peaks around 14:00, lowest at 05:00
        temp = self._base_temp + 7.0 * math.sin((hour - 8.0) * math.pi / 12.0)
        # Humidity is inversely related to temperature
        humidity = max(20.0, min(95.0, 65.0 - 25.0 * math.sin((hour - 8.0) * math.pi / 12.0)))
        dew_point = temp - ((100.0 - humidity) / 5.0)
        pressure = 1012.0 + 3.0 * math.cos(hour * 2 * math.pi / 24.0)

        # Wind speed lower at night (calm), higher in mid-afternoon
        wind_speed = max(0.5, 3.5 + 2.0 * math.sin((hour - 9.0) * math.pi / 12.0))
        # Predominant Delhi winter wind: North-Westerly (~300 - 320 degrees)
        wind_dir = (305.0 + 15.0 * math.sin(hour * math.pi / 12.0)) % 360.0
        wind_gusts = wind_speed * 1.4

        # Boundary layer height (PBLH): collapses to ~100-200m at night, rises to ~1500m at day
        pblh = max(100.0, 800.0 + 700.0 * math.sin((hour - 8.0) * math.pi / 12.0))
        precip = 0.0

        return (
            round(temp, 1),
            round(humidity, 1),
            round(dew_point, 1),
            round(pressure, 1),
            round(wind_speed, 1),
            round(wind_dir, 1),
            round(wind_gusts, 1),
            round(pblh, 1),
            precip,
        )

    def fetch_current_weather(self, latitude: float, longitude: float) -> WeatherObservation:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        (
            temp,
            humidity,
            dew_point,
            pressure,
            wind_speed,
            wind_dir,
            wind_gusts,
            pblh,
            precip,
        ) = self._generate_point(latitude, longitude, now)

        return WeatherObservation(
            latitude=latitude,
            longitude=longitude,
            timestamp=now,
            temperature_2m=temp,
            relative_humidity_2m=humidity,
            dew_point_2m=dew_point,
            surface_pressure=pressure,
            wind_speed_10m=wind_speed,
            wind_direction_10m=wind_dir,
            wind_gusts_10m=wind_gusts,
            boundary_layer_height=pblh,
            precipitation=precip,
            provider=self.provider_name,
        )

    def fetch_historical_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
    ) -> list[WeatherObservation]:
        results: list[WeatherObservation] = []
        current = start_date
        while current <= end_date:
            (
                temp,
                humidity,
                dew_point,
                pressure,
                wind_speed,
                wind_dir,
                wind_gusts,
                pblh,
                precip,
            ) = self._generate_point(latitude, longitude, current)

            results.append(
                WeatherObservation(
                    latitude=latitude,
                    longitude=longitude,
                    timestamp=current if current.tzinfo else current.replace(tzinfo=timezone.utc),
                    temperature_2m=temp,
                    relative_humidity_2m=humidity,
                    dew_point_2m=dew_point,
                    surface_pressure=pressure,
                    wind_speed_10m=wind_speed,
                    wind_direction_10m=wind_dir,
                    wind_gusts_10m=wind_gusts,
                    boundary_layer_height=pblh,
                    precipitation=precip,
                    provider=self.provider_name,
                )
            )
            current += timedelta(hours=1)
        return results

    def fetch_forecast_weather(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 3,
    ) -> list[WeatherForecast]:
        results: list[WeatherForecast] = []
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        total_hours = forecast_days * 24

        for h in range(1, total_hours + 1):
            future_dt = now + timedelta(hours=h)
            (
                temp,
                humidity,
                dew_point,
                pressure,
                wind_speed,
                wind_dir,
                wind_gusts,
                pblh,
                precip,
            ) = self._generate_point(latitude, longitude, future_dt)

            results.append(
                WeatherForecast(
                    latitude=latitude,
                    longitude=longitude,
                    timestamp=future_dt,
                    temperature_2m=temp,
                    relative_humidity_2m=humidity,
                    dew_point_2m=dew_point,
                    surface_pressure=pressure,
                    wind_speed_10m=wind_speed,
                    wind_direction_10m=wind_dir,
                    wind_gusts_10m=wind_gusts,
                    boundary_layer_height=pblh,
                    precipitation=precip,
                    provider=self.provider_name,
                    forecast_run_time=now,
                    forecast_horizon_hours=h,
                )
            )
        return results
