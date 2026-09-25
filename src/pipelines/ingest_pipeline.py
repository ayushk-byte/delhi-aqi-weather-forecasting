"""Ingestion pipeline coordinator: fetches AQI and weather, persists raw data with date partitions."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.config import get_settings
from src.core.logging import get_logger
from src.ingestion import get_aqi_provider, get_weather_provider
from src.ingestion.base import (
    AQIObservation,
    BaseAQIProvider,
    BaseWeatherProvider,
)
from src.storage.postgres import persist_air_quality, persist_weather

logger = get_logger(__name__)


class IngestionPipeline:
    """Orchestrates pulling live AQI and weather data and saving to the raw data store."""

    def __init__(
        self,
        aqi_provider: BaseAQIProvider | None = None,
        weather_provider: BaseWeatherProvider | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.settings = get_settings()
        self.aqi_provider = aqi_provider or get_aqi_provider()
        self.weather_provider = weather_provider or get_weather_provider()
        self.output_dir = output_dir or self.settings.resolve_path(self.settings.data_dir)

    def _get_partition_path(self, base_subfolder: str, dt: datetime, prefix: str) -> Path:
        """Create a date-partitioned directory: base/YYYY/MM/DD/prefix_YYYYMMDD_HH.json."""
        date_folder = self.output_dir / "raw" / base_subfolder / dt.strftime("%Y/%m/%d")
        date_folder.mkdir(parents=True, exist_ok=True)
        filename = f"{prefix}_{dt.strftime('%Y%m%d_%H%M%S')}.json"
        return date_folder / filename

    def run_aqi_ingestion(self) -> list[AQIObservation]:
        """Fetch latest AQI observations and write to raw partitioned storage."""
        logger.info(f"Starting AQI ingestion using provider: {self.aqi_provider.provider_name}")
        observations = self.aqi_provider.fetch_latest_observations()

        if observations:
            now = datetime.now(timezone.utc)
            file_path = self._get_partition_path("aqi", now, "aqi_obs")
            records = [obs.model_dump(mode="json") for obs in observations]

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str)

            logger.info(f"Successfully ingested {len(observations)} AQI records to {file_path}")
            if os.getenv("DATABASE_URL"):
                persist_air_quality(observations)
        else:
            logger.warning("No AQI observations returned by provider.")

        return observations

    def run_weather_ingestion(self) -> dict[str, Any]:
        """Fetch current weather and upcoming NWP forecasts for Delhi center and stations."""
        logger.info(
            f"Starting weather ingestion using provider: {self.weather_provider.provider_name}"
        )
        now = datetime.now(timezone.utc)

        # Ingest center weather + forecast
        center_lat = self.settings.bounding_box.min_lat + (
            (self.settings.bounding_box.max_lat - self.settings.bounding_box.min_lat) / 2.0
        )
        center_lon = self.settings.bounding_box.min_lon + (
            (self.settings.bounding_box.max_lon - self.settings.bounding_box.min_lon) / 2.0
        )

        current_obs = self.weather_provider.fetch_current_weather(center_lat, center_lon)
        if os.getenv("DATABASE_URL"):
            persist_weather(current_obs)
        forecasts = self.weather_provider.fetch_forecast_weather(
            center_lat, center_lon, forecast_days=3
        )

        weather_payload = {
            "ingested_at": now.isoformat(),
            "center": {
                "latitude": center_lat,
                "longitude": center_lon,
                "current": current_obs.model_dump(mode="json"),
                "forecasts": [f.model_dump(mode="json") for f in forecasts],
            },
        }

        file_path = self._get_partition_path("weather", now, "weather_feed")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(weather_payload, f, indent=2, default=str)

        logger.info(
            f"Successfully ingested weather: 1 current observation and {len(forecasts)} forecast horizons to {file_path}"
        )
        return weather_payload

    def run(self) -> dict[str, Any]:
        """Execute complete ingestion pipeline for both air quality and weather."""
        start_time = datetime.now(timezone.utc)
        logger.info(f"Ingestion pipeline started at {start_time.isoformat()}")

        aqi_records = self.run_aqi_ingestion()
        weather_data = self.run_weather_ingestion()
        if not aqi_records:
            raise RuntimeError(
                f"{self.aqi_provider.provider_name} returned no valid timestamped air-quality observations."
            )
        if not weather_data.get("center", {}).get("current", {}).get("timestamp"):
            raise RuntimeError(
                f"{self.weather_provider.provider_name} returned no timestamped weather observation."
            )

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        summary = {
            "status": "success",
            "timestamp": start_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "aqi_records_count": len(aqi_records),
            "weather_forecast_count": len(weather_data.get("center", {}).get("forecasts", [])),
            "aqi_provider": self.aqi_provider.provider_name,
            "weather_provider": self.weather_provider.provider_name,
        }
        logger.info(f"Ingestion pipeline completed in {duration:.2f}s: {summary}")
        return summary


def main() -> None:
    """CLI entrypoint for running ingestion."""
    parser = argparse.ArgumentParser(description="Delhi AQI & Weather Ingestion Pipeline")
    parser.add_argument(
        "--aqi-provider",
        choices=["mock", "openaq", "cpcb"],
        help="Air quality provider to use",
    )
    parser.add_argument(
        "--weather-provider",
        choices=["mock", "open_meteo"],
        help="Weather provider to use",
    )
    args = parser.parse_args()

    aqi_prov = get_aqi_provider(args.aqi_provider) if args.aqi_provider else None
    weather_prov = get_weather_provider(args.weather_provider) if args.weather_provider else None

    pipeline = IngestionPipeline(aqi_provider=aqi_prov, weather_provider=weather_prov)
    result = pipeline.run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
