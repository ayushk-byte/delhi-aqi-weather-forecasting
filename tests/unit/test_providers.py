"""Unit tests for Ingestion Providers."""

from datetime import datetime, timezone

import pytest

from src.ingestion import get_aqi_provider, get_weather_provider
from src.ingestion.aqi.mock_provider import MockAQIProvider
from src.ingestion.base import AQIObservation, WeatherForecast, WeatherObservation
from src.ingestion.weather.mock_weather import MockWeatherProvider
from src.ingestion.weather.open_meteo_provider import OpenMeteoProvider


def test_mock_aqi_provider_latest() -> None:
    provider = MockAQIProvider()
    assert provider.provider_name == "mock_aqi"

    obs = provider.fetch_latest_observations()
    assert len(obs) >= 8
    first = obs[0]
    assert isinstance(first, AQIObservation)
    assert first.station_id.startswith("DL")
    assert first.pm25 is not None and first.pm25 > 0
    assert first.pm10 is not None and first.pm10 >= first.pm25
    assert first.timestamp.tzinfo is not None


def test_mock_aqi_provider_historical() -> None:
    provider = MockAQIProvider()
    start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)
    obs = provider.fetch_historical_observations(start, end, station_ids=["DL001"])
    assert len(obs) == 6  # 6 hourly points inclusive
    assert all(o.station_id == "DL001" for o in obs)


def test_mock_weather_provider_current() -> None:
    provider = MockWeatherProvider()
    assert provider.provider_name == "mock_weather"

    obs = provider.fetch_current_weather(28.6139, 77.2090)
    assert isinstance(obs, WeatherObservation)
    assert obs.temperature_2m is not None
    assert obs.relative_humidity_2m is not None
    assert obs.boundary_layer_height is not None
    assert obs.boundary_layer_height >= 100.0


def test_mock_weather_provider_forecast() -> None:
    provider = MockWeatherProvider()
    forecasts = provider.fetch_forecast_weather(28.6139, 77.2090, forecast_days=2)
    assert len(forecasts) == 48
    first = forecasts[0]
    assert isinstance(first, WeatherForecast)
    assert first.forecast_horizon_hours == 1
    assert forecasts[-1].forecast_horizon_hours == 48


def test_provider_factories() -> None:
    aqi_mock = get_aqi_provider("mock")
    assert isinstance(aqi_mock, MockAQIProvider)

    wx_mock = get_weather_provider("mock")
    assert isinstance(wx_mock, MockWeatherProvider)

    wx_meteo = get_weather_provider("open_meteo")
    assert isinstance(wx_meteo, OpenMeteoProvider)

    with pytest.raises(ValueError):
        get_aqi_provider("non_existent_provider")

    with pytest.raises(ValueError):
        get_weather_provider("non_existent_provider")
