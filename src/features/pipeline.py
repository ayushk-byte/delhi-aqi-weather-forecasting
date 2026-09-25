"""Feature Pipeline orchestrator: transforms harmonized data into model-ready matrices."""

from pathlib import Path

import pandas as pd

from src.core.config import get_settings
from src.core.logging import get_logger
from src.features.atmospheric_features import create_all_atmospheric_features
from src.features.lag_features import create_all_lag_features
from src.features.temporal_features import add_temporal_cyclical_features

logger = get_logger(__name__)


class FeaturePipeline:
    """End-to-end feature creation and target labeling for multi-horizon coupled forecasting."""

    def __init__(
        self,
        horizons_hours: list[int] | None = None,
        target_pollutants: list[str] | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.settings = get_settings()
        self.horizons = horizons_hours or self.settings.horizons_hours
        self.target_pollutants = target_pollutants or self.settings.target_pollutants
        self.output_dir = output_dir or self.settings.resolve_path(self.settings.features_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply full suite of atmospheric, cyclical, and lag transformations."""
        logger.info(f"Extracting features from dataset with {len(df)} rows...")

        # 1. Atmospheric dispersion features
        df_feat = create_all_atmospheric_features(df)

        # 2. Temporal cyclical features
        df_feat = add_temporal_cyclical_features(df_feat)

        # 3. Autoregressive lags & rolling stats
        df_feat = create_all_lag_features(df_feat)

        logger.info(f"Feature extraction complete. Total columns: {len(df_feat.columns)}")
        return df_feat

    def add_target_horizons(
        self,
        df: pd.DataFrame,
        station_col: str = "station_id",
    ) -> pd.DataFrame:
        """Create forward-looking target columns (e.g. target_pm25_lead_6h, target_pm25_lead_24h)."""
        res = df.copy()

        for pol in self.target_pollutants:
            if pol not in res.columns:
                continue
            for h in self.horizons:
                target_col_name = f"target_{pol}_lead_{h}h"
                res[target_col_name] = res.groupby(station_col)[pol].shift(-h)

        return res

    def get_feature_columns(self, df: pd.DataFrame) -> list[str]:
        """Identify predictor columns, strictly excluding targets, identifiers, and timestamps."""
        excluded_prefixes = ("target_", "sub_index_")
        excluded_exact = {
            "timestamp",
            "station_id",
            "cpcb_aqi",
            "aqi_category",
            "provider",
            "raw_payload",
            "hourly_dt",
            "latitude",
            "longitude",
        }

        feature_cols = [
            c
            for c in df.columns
            if c not in excluded_exact
            and not any(c.startswith(p) for p in excluded_prefixes)
            and pd.api.types.is_numeric_dtype(df[c])
        ]
        return sorted(feature_cols)

    def prepare_training_dataset(
        self,
        df: pd.DataFrame,
        save_parquet: bool = True,
    ) -> tuple[pd.DataFrame, list[str]]:
        """Run feature extraction + target labeling, drop unlabelled rows, and optionally save."""
        df_feat = self.extract_features(df)
        df_targets = self.add_target_horizons(df_feat)
        feature_cols = self.get_feature_columns(df_targets)

        # Drop rows where target for the minimum horizon is missing
        primary_target = f"target_{self.target_pollutants[0]}_lead_{self.horizons[0]}h"
        if primary_target in df_targets.columns:
            valid_mask = df_targets[primary_target].notna()
            df_ready = df_targets[valid_mask].copy().reset_index(drop=True)
        else:
            df_ready = df_targets

        if save_parquet and not df_ready.empty:
            out_path = self.output_dir / "training_features.parquet"
            df_ready.to_parquet(out_path, index=False)
            logger.info(f"Saved training dataset with {len(df_ready)} rows to {out_path}")

        return df_ready, feature_cols

    def prepare_inference_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate features for the latest available timestamp per station for live inference."""
        df_feat = self.extract_features(df)

        # Get latest available row for each station
        latest_idx = df_feat.groupby("station_id")["timestamp"].idxmax()
        inference_slice = df_feat.loc[latest_idx].copy().reset_index(drop=True)

        return inference_slice
