"""Unit tests for OpenAQProvider HTTP response parsing and station matching."""

from unittest.mock import MagicMock, patch

from src.ingestion.aqi.openaq_provider import OpenAQProvider


def test_openaq_matching_and_parsing() -> None:
    provider = OpenAQProvider()

    # Anand Vihar coordinates: 28.6473, 77.3158
    locations_resp = MagicMock()
    locations_resp.json.return_value = {
        "results": [
            {
                "id": 1234,
                "name": "Anand Vihar Station",
                "coordinates": {"latitude": 28.6470, "longitude": 77.3150},
                "sensors": [
                    {
                        "id": 1,
                        "parameter": {"name": "pm25", "units": "µg/m³"},
                    },
                    {
                        "id": 2,
                        "parameter": {"name": "pm10", "units": "µg/m³"},
                    },
                    {
                        "id": 3,
                        "parameter": {"name": "no2", "units": "µg/m³"},
                    },
                ],
            }
        ]
    }
    latest_resp = MagicMock()
    latest_resp.json.return_value = {
        "results": [
            {"sensorsId": 1, "value": 142.5, "datetime": {"utc": "2026-09-24T12:00:00Z"}},
            {"sensorsId": 2, "value": 260.0, "datetime": {"utc": "2026-09-24T12:00:00Z"}},
            {"sensorsId": 3, "value": 45.0, "datetime": {"utc": "2026-09-24T12:00:00Z"}},
        ]
    }
    latest_resp.raise_for_status.return_value = None
    locations_resp.raise_for_status.return_value = None

    with patch("httpx.Client.get", side_effect=[locations_resp, latest_resp]):
        obs = provider.fetch_latest_observations()

    assert len(obs) == 1
    record = obs[0]
    assert record.station_id == "DL001"  # Matched to Anand Vihar
    assert record.pm25 == 142.5
    assert record.pm10 == 260.0
    assert record.no2 == 45.0
    assert record.provider == "openaq"


def test_openaq_normalizes_gas_units() -> None:
    value = OpenAQProvider._normalize_value("no2", 0.05, "ppm")
    assert round(value, 2) == 94.08
