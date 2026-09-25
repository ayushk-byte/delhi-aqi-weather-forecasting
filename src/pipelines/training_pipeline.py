"""Training pipeline runner: ingests historical data, builds features, trains & benchmarks models."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.config import get_settings
from src.core.logging import get_logger
from src.features.pipeline import FeaturePipeline
from src.modeling.registry import ModelRegistry
from src.modeling.trainer import ModelTrainer

logger = get_logger(__name__)


class TrainingPipeline:
    """Orchestrates end-to-end retraining, feature preparation, model comparison, and registration."""

    def __init__(
        self,
        target_pollutant: str = "pm25",
        horizons_hours: list[int] | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.settings = get_settings()
        self.target_pollutant = target_pollutant
        self.horizons = horizons_hours or self.settings.horizons_hours
        self.data_dir = data_dir or self.settings.resolve_path(self.settings.data_dir)

    def load_or_create_harmonized_data(self, history_days: int = 14) -> pd.DataFrame:
        """Load only an aligned dataset whose real-provider provenance was verified."""
        processed_file = self.data_dir / "processed" / "aligned_observations.parquet"
        provenance_file = processed_file.with_suffix(".provenance.json")

        if processed_file.exists():
            provenance = (
                json.loads(provenance_file.read_text(encoding="utf-8"))
                if provenance_file.exists()
                else {}
            )
            if not provenance.get("real_observations_verified"):
                raise RuntimeError(
                    "Training data provenance is missing or includes mock sources. "
                    "Rebuild the aligned dataset from verified real observations."
                )
            logger.info(f"Loading existing harmonized dataset from {processed_file}")
            return pd.read_parquet(processed_file)
        raise RuntimeError(
            "No real aligned training observations are available. Synthetic training data "
            "generation is disabled."
        )

    def run(self) -> dict[str, Any]:
        """Execute end-to-end model training workflow."""
        start_time = datetime.now(timezone.utc)
        logger.info(f"Training pipeline started at {start_time.isoformat()}")

        # 1. Harmonized dataset
        harmonized_df = self.load_or_create_harmonized_data()

        # 2. Feature pipeline
        feature_pipe = FeaturePipeline(
            horizons_hours=self.horizons,
            target_pollutants=[self.target_pollutant],
            output_dir=self.data_dir / "features",
        )
        df_train, feature_cols = feature_pipe.prepare_training_dataset(
            harmonized_df, save_parquet=True
        )

        # 3. Model benchmarking and registration
        registry = ModelRegistry()
        trainer = ModelTrainer(
            target_pollutant=self.target_pollutant,
            horizons_hours=self.horizons,
            registry=registry,
        )
        report = trainer.train_and_evaluate_all(df_train, feature_cols)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        report["duration_seconds"] = round(duration, 2)
        logger.info(f"Training pipeline completed in {duration:.2f}s.")
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Delhi AQI Model Training & Benchmarking Pipeline")
    parser.add_argument(
        "--pollutant", default="pm25", choices=["pm25", "pm10"], help="Target pollutant"
    )
    args = parser.parse_args()

    pipeline = TrainingPipeline(target_pollutant=args.pollutant)
    report = pipeline.run()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
