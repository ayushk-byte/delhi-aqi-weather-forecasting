"""Real-time inference pipeline: generates multi-horizon predictions, hotspots, explanations, and alerts."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.config import get_settings
from src.core.constants import DELHI_STATIONS
from src.core.logging import get_logger
from src.features.pipeline import FeaturePipeline
from src.modeling.alerts import generate_forecast_alerts
from src.modeling.explainability import ForecastExplainer
from src.modeling.registry import ModelRegistry
from src.preprocessing.aqi_calculator import calculate_sub_index, get_aqi_category
from src.spatial.hotspots import detect_hotspots, generate_spatial_grid

logger = get_logger(__name__)


class InferencePipeline:
    """Orchestrates pulling latest observation state, computing features, forecasts, hotspots, XAI, and alerts."""

    def __init__(
        self,
        registry: ModelRegistry | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.settings = get_settings()
        self.registry = registry or ModelRegistry()
        self.data_dir = data_dir or self.settings.resolve_path(self.settings.data_dir)
        self.feature_pipeline = FeaturePipeline(
            horizons_hours=self.settings.horizons_hours,
            output_dir=self.data_dir / "features",
        )
        self.explainer = ForecastExplainer()

    def load_recent_history(self, hours_needed: int = 36) -> pd.DataFrame:
        """Load recent harmonized observation history required for lag feature computation."""
        processed_file = self.data_dir / "processed" / "aligned_observations.parquet"

        if processed_file.exists():
            df = pd.read_parquet(processed_file)
            provenance_file = processed_file.with_suffix(".provenance.json")
            provenance = (
                json.loads(provenance_file.read_text(encoding="utf-8"))
                if provenance_file.exists()
                else {}
            )
            if not provenance.get("real_observations_verified"):
                raise RuntimeError(
                    "Forecast unavailable: the aligned dataset has no verified real-provider "
                    "provenance. Rebuild it from real observations before inference."
                )
            if not df.empty and "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                latest_ts = df["timestamp"].max()
                cutoff = latest_ts - timedelta(hours=hours_needed)
                recent = df[df["timestamp"] >= cutoff].copy().reset_index(drop=True)
                if len(recent) >= 10:
                    return recent

        raise RuntimeError(
            "Forecast unavailable: at least 10 recent, real, aligned observation rows are required. "
            "No synthetic observations are substituted."
        )

    def run_inference(self) -> dict[str, Any]:
        """Execute real-time coupled forecast with spatial hotspots, XAI explanations, and alerts."""
        start_time = datetime.now(timezone.utc)
        logger.info(f"Running inference at {start_time.isoformat()}...")

        # 1. Load recent history and extract latest inference feature row per station
        recent_df = self.load_recent_history()
        inference_features = self.feature_pipeline.prepare_inference_features(recent_df)

        if inference_features.empty:
            raise ValueError("No inference features could be extracted from recent observations.")

        latest_timestamp = pd.to_datetime(inference_features["timestamp"].max(), utc=True)

        # 2. Load champion model for PM2.5
        champion_pm25 = self.registry.get_champion_model("pm25")
        feature_cols = self.feature_pipeline.get_feature_columns(inference_features)
        X = inference_features[feature_cols]

        pm25_preds_by_horizon = champion_pm25.predict(X)

        # 3. Assemble station-level forecasts with uncertainty and XAI explanations
        stations_forecasts = []
        station_explanations: dict[str, dict[int, Any]] = {}
        city_pm25_by_horizon: dict[int, list[float]] = {h: [] for h in champion_pm25.horizons_hours}
        city_aqi_by_horizon: dict[int, list[float]] = {h: [] for h in champion_pm25.horizons_hours}

        for idx, row in inference_features.iterrows():
            st_id = str(row["station_id"])
            meta = DELHI_STATIONS.get(st_id, {})
            st_name = meta.get("name", f"Station {st_id}")
            lat = meta.get("latitude", self.settings.bounding_box.min_lat)
            lon = meta.get("longitude", self.settings.bounding_box.min_lon)

            if "pm25" not in row or pd.isna(row["pm25"]):
                continue
            current_val = float(row["pm25"])
            current_aqi = calculate_sub_index("pm25", current_val)
            if current_aqi is None:
                continue

            st_horizons = []
            st_expl_map = {}

            for h in champion_pm25.horizons_hours:
                pred_pm25 = float(pm25_preds_by_horizon[h][idx])
                pred_pm10 = None

                sub_idx = calculate_sub_index("pm25", pred_pm25) or round(pred_pm25)
                category = get_aqi_category(sub_idx)

                # Uncertainty calculation
                # No calibrated residual distribution is registered, so uncertainty is unavailable.
                unc = {
                    "uncertainty_lower": None,
                    "uncertainty_upper": None,
                    "confidence_score_pct": None,
                }

                target_dt = latest_timestamp + timedelta(hours=h)

                # Explainability derivation
                feature_importances = getattr(champion_pm25, "feature_importances", {}).get(h, {})
                explanation = self.explainer.explain_forecast(
                    station_id=st_id,
                    horizon_hours=h,
                    predicted_aqi=sub_idx,
                    current_aqi=current_aqi,
                    feature_row=row,
                    feature_importances=feature_importances,
                )
                st_expl_map[h] = explanation

                st_horizons.append(
                    {
                        "horizon_hours": h,
                        "forecast_timestamp": target_dt.isoformat(),
                        "predicted_pm25": round(pred_pm25, 1),
                        "predicted_pm10": pred_pm10,
                        "predicted_aqi": round(sub_idx),
                        "aqi_category": category,
                        "dominant_pollutant": "pm25",
                        "uncertainty_lower": unc["uncertainty_lower"],
                        "uncertainty_upper": unc["uncertainty_upper"],
                        "confidence_score_pct": unc["confidence_score_pct"],
                    }
                )
                city_pm25_by_horizon[h].append(pred_pm25)
                city_aqi_by_horizon[h].append(sub_idx)

            station_explanations[st_id] = st_expl_map

            stations_forecasts.append(
                {
                    "station_id": st_id,
                    "station_name": st_name,
                    "latitude": lat,
                    "longitude": lon,
                    "current_pm25": round(current_val, 1),
                    "current_aqi": round(current_aqi),
                    "horizons": st_horizons,
                }
            )

        if not stations_forecasts:
            raise RuntimeError("Forecast unavailable: no valid measured PM2.5 inputs are present.")

        # 4. Regional city-wide summary with confidence
        city_summary = []
        for h in champion_pm25.horizons_hours:
            vals = city_pm25_by_horizon[h]
            aqi_vals = city_aqi_by_horizon[h]
            mean_aqi = round(float(np.mean(aqi_vals)))
            cat = get_aqi_category(mean_aqi)
            unc = {
                "uncertainty_lower": None,
                "uncertainty_upper": None,
                "confidence_score_pct": None,
            }

            city_summary.append(
                {
                    "horizon_hours": h,
                    "forecast_timestamp": (latest_timestamp + timedelta(hours=h)).isoformat(),
                    "city_mean_pm25": round(float(np.mean(vals)), 1),
                    "city_max_pm25": round(float(np.max(vals)), 1),
                    "city_min_pm25": round(float(np.min(vals)), 1),
                    "city_mean_aqi": mean_aqi,
                    "aqi_category": cat,
                    "uncertainty_lower": unc["uncertainty_lower"],
                    "uncertainty_upper": unc["uncertainty_upper"],
                    "confidence_score_pct": unc["confidence_score_pct"],
                }
            )

        # 5. Hotspot Detection (+24h and +48h primary horizons)
        hotspots_24h = detect_hotspots(stations_forecasts, horizon_hours=24)
        hotspots_48h = detect_hotspots(stations_forecasts, horizon_hours=48)

        # 6. Spatial 2D Grid Interpolation (for continuous map contours)
        spatial_grid_24h = generate_spatial_grid(
            stations_forecasts, horizon_hours=24, grid_steps=12
        )

        # 7. Forecast-Based Decision Alerts
        alerts = generate_forecast_alerts(
            station_predictions=stations_forecasts,
            city_summary=city_summary,
        )

        result = {
            "status": "success",
            "input_data_source": "validated_stored_observations",
            "generated_at": start_time.isoformat(),
            "latest_observation_timestamp": latest_timestamp.isoformat(),
            "model_name": champion_pm25.name,
            "target_pollutant": "pm25",
            "city_summary": city_summary,
            "stations": stations_forecasts,
            "hotspots": {
                "horizon_24h": hotspots_24h,
                "horizon_48h": hotspots_48h,
            },
            "spatial_grid": spatial_grid_24h,
            "explanations": station_explanations,
            "alerts": alerts,
        }

        # 8. Persist to disk for rapid sub-millisecond serving
        cache_dir = self.data_dir / "processed"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "latest_forecast.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)

        logger.info(
            f"Inference cycle completed in {(datetime.now(timezone.utc) - start_time).total_seconds():.2f}s. "
            f"Detected {len(hotspots_24h)} +24h hotspots, generated {len(alerts)} alerts."
        )
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Delhi AQI Real-time Inference Pipeline")
    parser.parse_args()

    pipeline = InferencePipeline()
    res = pipeline.run_inference()
    print(
        json.dumps(
            {
                "city_summary": res["city_summary"],
                "hotspots_24h": res["hotspots"]["horizon_24h"],
                "alerts": res["alerts"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
