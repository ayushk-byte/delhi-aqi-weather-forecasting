"""Unit tests for the Ingestion Pipeline runner."""

from pathlib import Path

from src.ingestion.aqi.mock_provider import MockAQIProvider
from src.ingestion.weather.mock_weather import MockWeatherProvider
from src.pipelines.ingest_pipeline import IngestionPipeline


def test_ingestion_pipeline_run(tmp_path: Path) -> None:
    aqi_prov = MockAQIProvider()
    wx_prov = MockWeatherProvider()

    pipeline = IngestionPipeline(
        aqi_provider=aqi_prov,
        weather_provider=wx_prov,
        output_dir=tmp_path,
    )

    summary = pipeline.run()

    assert summary["status"] == "success"
    assert summary["aqi_records_count"] >= 8
    assert summary["weather_forecast_count"] == 72
    assert summary["aqi_provider"] == "mock_aqi"
    assert summary["weather_provider"] == "mock_weather"

    # Verify partitioned files exist on disk
    aqi_files = list((tmp_path / "raw" / "aqi").glob("**/*.json"))
    weather_files = list((tmp_path / "raw" / "weather").glob("**/*.json"))

    assert len(aqi_files) >= 1
    assert len(weather_files) >= 1
