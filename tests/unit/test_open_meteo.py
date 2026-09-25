"""Unit tests for OpenMeteoProvider HTTP response parsing."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src.ingestion.weather.open_meteo_provider import OpenMeteoProvider


def test_open_meteo_current_parsing() -> None:
    provider = OpenMeteoProvider()

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "current": {
            "time": "2026-09-24T12:00",
            "temperature_2m": 31.5,
            "relative_humidity_2m": 55.0,
            "surface_pressure": 1008.2,
            "wind_speed_10m": 3.8,
            "wind_direction_10m": 290.0,
            "precipitation": 0.0,
        }
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client.get", return_value=mock_resp) as get:
        obs = provider.fetch_current_weather(28.6139, 77.2090)

    assert obs.latitude == 28.6139
    assert obs.temperature_2m == 31.5
    assert obs.relative_humidity_2m == 55.0
    assert obs.wind_speed_10m == 3.8
    assert obs.wind_direction_10m == 290.0
    assert obs.provider == "open_meteo"
    assert get.call_args.kwargs["params"]["wind_speed_unit"] == "ms"


def test_open_meteo_forecast_parsing() -> None:
    provider = OpenMeteoProvider()
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    forecast_times = [
        (start + timedelta(hours=hour)).strftime("%Y-%m-%dT%H:%M") for hour in (1, 2, 3)
    ]

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "hourly": {
            "time": forecast_times,
            "temperature_2m": [25.0, 24.5, 24.0],
            "relative_humidity_2m": [70.0, 75.0, 80.0],
            "dew_point_2m": [19.0, 19.5, 20.0],
            "surface_pressure": [1010.0, 1010.5, 1011.0],
            "wind_speed_10m": [2.5, 2.0, 1.8],
            "wind_direction_10m": [310.0, 315.0, 320.0],
            "wind_gusts_10m": [4.0, 3.5, 3.0],
            "boundary_layer_height": [300.0, 250.0, 200.0],
            "precipitation": [0.0, 0.0, 0.0],
        }
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client.get", return_value=mock_resp):
        forecasts = provider.fetch_forecast_weather(28.6139, 77.2090, forecast_days=1)

    assert len(forecasts) >= 1
    for f in forecasts:
        assert f.temperature_2m is not None
        assert f.boundary_layer_height is not None
        assert f.provider == "open_meteo"
