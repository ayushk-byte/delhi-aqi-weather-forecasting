"""Harmonizer: Coordinates validation, temporal/spatial alignment, and AQI computation."""

import json
from pathlib import Path

import pandas as pd

from src.core.config import get_settings
from src.core.logging import get_logger
from src.preprocessing.aqi_calculator import calculate_aqi_dataframe
from src.preprocessing.spatial_alignment import attach_weather_to_stations
from src.preprocessing.temporal_alignment import align_hourly_timeseries
from src.validation.quality_checks import clean_dataset

logger = get_logger(__name__)


class DataHarmonizer:
    """End-to-end preprocessing workflow to convert raw AQI and weather feeds into clean aligned data."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.settings = get_settings()
        self.output_dir = output_dir or self.settings.resolve_path(self.settings.processed_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def harmonize(
        self,
        aqi_df: pd.DataFrame,
        weather_df: pd.DataFrame,
        save_parquet: bool = True,
    ) -> pd.DataFrame:
        """Execute full cleaning, alignment, and CPCB calculation pipeline.

        Args:
            aqi_df: Raw AQI DataFrame with station_id, timestamp, pollutants.
            weather_df: Raw weather DataFrame with timestamp, temperature, wind, etc.
            save_parquet: If True, writes result to data/processed/aligned_observations.parquet.
        """
        logger.info("Starting data harmonization pipeline...")

        # 1. Quality checks and cleaning on AQI
        cleaned_aqi, q_report = clean_dataset(aqi_df)
        logger.info(
            f"AQI cleaning complete: {q_report.out_of_bounds_anomalies} out-of-bounds, "
            f"{q_report.stuck_sensor_anomalies} stuck points masked."
        )

        # 2. Hourly temporal regularization
        aligned_aqi = align_hourly_timeseries(cleaned_aqi)
        logger.info(f"Temporal alignment complete: {len(aligned_aqi)} regularized station-hours.")

        # 3. Spatial alignment: attach weather features
        aligned_dataset = attach_weather_to_stations(aligned_aqi, weather_df)
        logger.info("Spatial alignment complete: meteorological features attached.")

        # 4. Compute CPCB AQI sub-indices and categories
        final_df = calculate_aqi_dataframe(aligned_dataset)
        logger.info("CPCB AQI sub-indices and categories computed.")

        # 5. Persist to Parquet
        if save_parquet and not final_df.empty:
            out_file = self.output_dir / "aligned_observations.parquet"
            final_df.to_parquet(out_file, index=False)
            aqi_providers = sorted(
                set(aqi_df.get("provider", pd.Series(dtype=str)).dropna().astype(str))
            )
            weather_providers = sorted(
                set(weather_df.get("provider", pd.Series(dtype=str)).dropna().astype(str))
            )
            providers = sorted(set(aqi_providers + weather_providers))
            provenance = {
                "providers": providers,
                "real_observations_verified": bool(aqi_providers and weather_providers)
                and all(not name.lower().startswith("mock") for name in providers),
            }
            (self.output_dir / "aligned_observations.provenance.json").write_text(
                json.dumps(provenance, indent=2), encoding="utf-8"
            )
            logger.info(f"Harmonized dataset saved to {out_file} ({len(final_df)} rows).")

        return final_df
