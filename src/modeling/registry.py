"""Model Registry: versioning, storage, and champion model management."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.config import get_settings
from src.core.logging import get_logger
from src.modeling.base import BaseForecaster
from src.modeling.baselines import PersistenceForecaster, SeasonalDiurnalLagForecaster
from src.modeling.coupled_model import WeatherCoupledForecaster

logger = get_logger(__name__)


class ModelRegistry:
    """Manages versioned model artifacts and champion selection on local disk."""

    def __init__(self, registry_dir: Path | None = None) -> None:
        self.settings = get_settings()
        self.registry_dir = (
            registry_dir or self.settings.resolve_path(self.settings.models_dir) / "registry"
        )
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def register_model(
        self,
        forecaster: BaseForecaster,
        metrics: dict[str, Any],
        is_champion: bool = False,
        version: str | None = None,
    ) -> Path:
        """Save a forecaster artifact, record its performance metrics, and optionally set as champion."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        v = version or f"v_{timestamp_str}"
        model_subfolder = self.registry_dir / f"{forecaster.target_pollutant}_{forecaster.name}_{v}"

        saved_path = forecaster.save(model_subfolder)

        # Write evaluation summary
        eval_record = {
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "model_name": forecaster.name,
            "target_pollutant": forecaster.target_pollutant,
            "version": v,
            "is_champion": is_champion,
            "metrics": metrics,
        }
        with open(saved_path / "evaluation.json", "w", encoding="utf-8") as f:
            json.dump(eval_record, f, indent=2)

        if is_champion:
            self._set_champion(forecaster.target_pollutant, saved_path)

        logger.info(f"Registered model {forecaster.name} (version {v}) at {saved_path}")
        return saved_path

    def _set_champion(self, target_pollutant: str, model_path: Path) -> None:
        champion_pointer = self.registry_dir / f"champion_{target_pollutant}.json"
        data = {
            "champion_path": str(model_path.resolve()),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(champion_pointer, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Updated champion pointer for {target_pollutant} -> {model_path.name}")

    def get_champion_model(self, target_pollutant: str = "pm25") -> BaseForecaster:
        """Load and return current champion model for given pollutant."""
        champion_pointer = self.registry_dir / f"champion_{target_pollutant}.json"

        if champion_pointer.exists():
            with open(champion_pointer, encoding="utf-8") as f:
                data = json.load(f)
            model_dir = Path(data["champion_path"])
            if model_dir.exists():
                return self._instantiate_model(model_dir)

        # Fallback to Persistence baseline if no champion registered
        logger.warning(
            f"No champion registered for {target_pollutant}. Falling back to default persistence forecaster."
        )
        forecaster = PersistenceForecaster(target_pollutant=target_pollutant)
        forecaster.is_fitted = True
        return forecaster

    def _instantiate_model(self, model_dir: Path) -> BaseForecaster:
        meta_file = model_dir / "metadata.json"
        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)

        name = meta.get("name")
        if name == "weather_coupled_lightgbm":
            return WeatherCoupledForecaster.load(model_dir)
        elif name == "seasonal_diurnal_baseline":
            return SeasonalDiurnalLagForecaster.load(model_dir)
        else:
            return PersistenceForecaster.load(model_dir)

    def list_models(self) -> list[dict[str, Any]]:
        """List all models registered in the registry."""
        models = []
        for d in self.registry_dir.iterdir():
            if d.is_dir() and (d / "metadata.json").exists():
                with open(d / "metadata.json", encoding="utf-8") as f:
                    meta = json.load(f)
                eval_metrics = {}
                if (d / "evaluation.json").exists():
                    with open(d / "evaluation.json", encoding="utf-8") as f:
                        eval_metrics = json.load(f).get("metrics", {})
                models.append(
                    {
                        "path": str(d),
                        "name": meta.get("name"),
                        "pollutant": meta.get("target_pollutant"),
                        "horizons": meta.get("horizons_hours"),
                        "metrics": eval_metrics,
                    }
                )
        return models
