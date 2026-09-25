"""Unit tests for atmospheric, temporal, and lag feature engineering."""

import numpy as np
import pandas as pd

from src.features.atmospheric_features import (
    add_ventilation_index,
    add_wind_components,
)
from src.features.lag_features import add_autoregressive_lags
from src.features.pipeline import FeaturePipeline
from src.features.temporal_features import add_temporal_cyclical_features


def test_wind_components() -> None:
    df = pd.DataFrame(
        {
            "wind_speed_10m": [10.0, 10.0],
            # 270 deg = West wind (blowing towards East -> u > 0, v = 0)
            # 360 deg = North wind (blowing towards South -> u = 0, v < 0)
            "wind_direction_10m": [270.0, 360.0],
        }
    )

    res = add_wind_components(df)
    assert np.isclose(res.loc[0, "wind_u"], 10.0, atol=1e-3)
    assert np.isclose(res.loc[0, "wind_v"], 0.0, atol=1e-3)
    assert np.isclose(res.loc[1, "wind_u"], 0.0, atol=1e-3)
    assert np.isclose(res.loc[1, "wind_v"], -10.0, atol=1e-3)


def test_ventilation_index() -> None:
    df = pd.DataFrame(
        {
            "wind_speed_10m": [2.0, 5.0],
            "boundary_layer_height": [500.0, 1200.0],
        }
    )

    res = add_ventilation_index(df)
    assert res.loc[0, "ventilation_index"] == 1000.0
    assert res.loc[0, "is_stagnation_ventilation"] == 1  # < 2000 m^2/s

    assert res.loc[1, "ventilation_index"] == 6000.0
    assert res.loc[1, "is_stagnation_ventilation"] == 0


def test_temporal_cyclical_features() -> None:
    # 24 consecutive hours
    times = pd.date_range("2026-01-01 00:00", periods=24, freq="1h", tz="UTC")
    df = pd.DataFrame({"timestamp": times})

    res = add_temporal_cyclical_features(df)

    assert "hour_sin" in res.columns
    assert "hour_cos" in res.columns
    assert "is_winter_pollution_season" in res.columns
    # Check trigonometric identity: sin^2 + cos^2 == 1
    trig_identity = res["hour_sin"] ** 2 + res["hour_cos"] ** 2
    assert np.allclose(trig_identity, 1.0, atol=1e-5)
    # January is winter pollution season
    assert (res["is_winter_pollution_season"] == 1).all()


def test_lag_features_per_station() -> None:
    times = pd.date_range("2026-01-01 00:00", periods=30, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "station_id": ["DL001"] * 30,
            "timestamp": times,
            "pm25": list(range(1, 31)),
        }
    )

    res = add_autoregressive_lags(df, columns=["pm25"], lags=[1, 24])

    assert np.isnan(res.loc[0, "pm25_lag_1h"])
    assert res.loc[1, "pm25_lag_1h"] == 1.0
    assert res.loc[25, "pm25_lag_24h"] == 2.0


def test_feature_pipeline_train_and_inference(tmp_path) -> None:
    # Build 72-hour synthetic history for two stations
    times = pd.date_range("2026-01-01 00:00", periods=72, freq="1h", tz="UTC")
    records = []
    for st in ["DL001", "DL002"]:
        for t in times:
            records.append(
                {
                    "station_id": st,
                    "timestamp": t,
                    "pm25": 100.0 + (t.hour * 2.0),
                    "pm10": 180.0 + (t.hour * 3.0),
                    "no2": 35.0,
                    "temperature_2m": 20.0 + t.hour * 0.5,
                    "relative_humidity_2m": 60.0,
                    "wind_speed_10m": 3.0,
                    "wind_direction_10m": 310.0,
                    "boundary_layer_height": 700.0,
                }
            )
    df_raw = pd.DataFrame(records)

    pipeline = FeaturePipeline(
        horizons_hours=[6, 24],
        target_pollutants=["pm25"],
        output_dir=tmp_path,
    )

    # 1. Training features
    df_train, feat_cols = pipeline.prepare_training_dataset(df_raw, save_parquet=True)
    assert not df_train.empty
    assert "target_pm25_lead_6h" in df_train.columns
    assert "target_pm25_lead_24h" in df_train.columns
    assert "wind_u" in feat_cols
    assert "ventilation_index" in feat_cols
    assert (tmp_path / "training_features.parquet").exists()

    # 2. Inference features
    df_infer = pipeline.prepare_inference_features(df_raw)
    assert len(df_infer) == 2  # exactly 1 row per station
    assert set(df_infer["station_id"]) == {"DL001", "DL002"}
