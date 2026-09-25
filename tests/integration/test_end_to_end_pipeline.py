"""Integration test covering Ingestion -> Validation -> Harmonization -> Feature Pipeline."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from src.features.pipeline import FeaturePipeline
from src.ingestion.aqi.mock_provider import MockAQIProvider
from src.ingestion.weather.mock_weather import MockWeatherProvider
from src.preprocessing.harmonizer import DataHarmonizer


def test_full_pipeline_flow(tmp_path: Path) -> None:
    # 1. Ingestion: Generate 72 hours of data
    start_dt = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(hours=72)

    aqi_prov = MockAQIProvider(base_pm25=150.0)
    wx_prov = MockWeatherProvider()

    raw_aqi_obs = aqi_prov.fetch_historical_observations(
        start_dt, end_dt, station_ids=["DL001", "DL002"]
    )
    raw_wx_obs = wx_prov.fetch_historical_weather(28.6139, 77.2090, start_dt, end_dt)

    aqi_df = pd.DataFrame([o.model_dump(mode="json") for o in raw_aqi_obs])
    wx_df = pd.DataFrame([w.model_dump(mode="json") for w in raw_wx_obs])

    # Convert timestamps
    aqi_df["timestamp"] = pd.to_datetime(aqi_df["timestamp"], utc=True)
    wx_df["timestamp"] = pd.to_datetime(wx_df["timestamp"], utc=True)

    # 2. Harmonization (Validation + Hourly alignment + Weather attachment + CPCB AQI)
    processed_dir = tmp_path / "processed"
    harmonizer = DataHarmonizer(output_dir=processed_dir)
    harmonized_df = harmonizer.harmonize(aqi_df, wx_df, save_parquet=True)

    assert not harmonized_df.empty
    assert (processed_dir / "aligned_observations.parquet").exists()
    assert "cpcb_aqi" in harmonized_df.columns
    assert "wind_speed_10m" in harmonized_df.columns

    # 3. Feature Engineering Pipeline (Atmospheric physics + Cyclical + Lags + Targets)
    features_dir = tmp_path / "features"
    pipeline = FeaturePipeline(
        horizons_hours=[6, 12, 24, 48],
        target_pollutants=["pm25", "pm10"],
        output_dir=features_dir,
    )

    df_train, feat_cols = pipeline.prepare_training_dataset(harmonized_df, save_parquet=True)

    assert not df_train.empty
    assert (features_dir / "training_features.parquet").exists()
    assert "wind_u" in feat_cols
    assert "wind_v" in feat_cols
    assert "ventilation_index" in feat_cols
    assert "is_winter_pollution_season" in feat_cols
    assert "pm25_lag_1h" in feat_cols
    assert "target_pm25_lead_6h" in df_train.columns
    assert "target_pm25_lead_24h" in df_train.columns
    assert "target_pm10_lead_48h" in df_train.columns

    # 4. Inference Slicing
    df_infer = pipeline.prepare_inference_features(harmonized_df)
    assert len(df_infer) == 2  # exactly 1 inference row per station
