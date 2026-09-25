"""Unit tests for ModelRegistry."""

from pathlib import Path

from src.modeling.baselines import PersistenceForecaster
from src.modeling.registry import ModelRegistry


def test_registry_registration_and_champion(tmp_path: Path) -> None:
    registry = ModelRegistry(registry_dir=tmp_path / "registry")

    model = PersistenceForecaster(target_pollutant="pm25", horizons_hours=[6, 24])
    model.is_fitted = True
    model.feature_columns = ["pm25"]

    dummy_metrics = {"average_mae": 15.2, "by_horizon": {6: {"mae": 12.0}, 24: {"mae": 18.4}}}

    saved_path = registry.register_model(
        forecaster=model,
        metrics=dummy_metrics,
        is_champion=True,
        version="v1.0.0",
    )

    assert saved_path.exists()
    assert (saved_path / "evaluation.json").exists()

    # Load champion
    champ = registry.get_champion_model(target_pollutant="pm25")
    assert champ.name == "persistence_baseline"
    assert champ.is_fitted is True

    # List models
    all_models = registry.list_models()
    assert len(all_models) == 1
    assert all_models[0]["name"] == "persistence_baseline"
