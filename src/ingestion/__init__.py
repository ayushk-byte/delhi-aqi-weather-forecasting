"""Ingestion package providing factory helpers and provider implementations."""

from src.core.config import get_settings
from src.ingestion.aqi.cpcb_provider import CPCBProvider
from src.ingestion.aqi.mock_provider import MockAQIProvider
from src.ingestion.aqi.openaq_provider import OpenAQProvider
from src.ingestion.base import (
    AQIObservation,
    BaseAQIProvider,
    BaseWeatherProvider,
    WeatherForecast,
    WeatherObservation,
)
from src.ingestion.weather.mock_weather import MockWeatherProvider
from src.ingestion.weather.open_meteo_provider import OpenMeteoProvider


def get_aqi_provider(name: str | None = None) -> BaseAQIProvider:
    """Factory to instantiate an AQI provider by identifier.

    Supported names: 'mock', 'openaq', 'cpcb'.
    """
    settings = get_settings()
    provider_type = (name or settings.aqi_provider).lower()

    if provider_type in ("mock", "mock_aqi"):
        return MockAQIProvider()
    elif provider_type == "openaq":
        return OpenAQProvider(
            api_key=settings.openaq_api_key,
            base_url=settings.openaq.base_url,
            timeout_seconds=float(settings.ingestion.timeout_seconds),
        )
    elif provider_type == "cpcb":
        return CPCBProvider(
            api_key=settings.data_gov_in_api_key,
            timeout_seconds=float(settings.ingestion.timeout_seconds),
        )
    else:
        raise ValueError(
            f"Unknown AQI provider: '{provider_type}'. Must be 'mock', 'openaq', or 'cpcb'."
        )


def get_weather_provider(name: str | None = None) -> BaseWeatherProvider:
    """Factory to instantiate a Weather provider by identifier.

    Supported names: 'mock', 'open_meteo'.
    """
    settings = get_settings()
    provider_type = (name or settings.weather_provider).lower()

    if provider_type in ("mock", "mock_weather"):
        return MockWeatherProvider()
    elif provider_type == "open_meteo":
        return OpenMeteoProvider(
            forecast_url=settings.open_meteo.forecast_url,
            historical_url=settings.open_meteo.historical_url,
            timeout_seconds=float(settings.ingestion.timeout_seconds),
        )
    else:
        raise ValueError(
            f"Unknown Weather provider: '{provider_type}'. Must be 'mock' or 'open_meteo'."
        )


__all__ = [
    "BaseAQIProvider",
    "BaseWeatherProvider",
    "AQIObservation",
    "WeatherObservation",
    "WeatherForecast",
    "MockAQIProvider",
    "OpenAQProvider",
    "CPCBProvider",
    "MockWeatherProvider",
    "OpenMeteoProvider",
    "get_aqi_provider",
    "get_weather_provider",
]
