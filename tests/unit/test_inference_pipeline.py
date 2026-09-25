"""Unit tests for the Inference Pipeline."""

from pathlib import Path

import pytest

from src.pipelines.inference_pipeline import InferencePipeline


def test_inference_pipeline_run(tmp_path: Path) -> None:
    pipeline = InferencePipeline(data_dir=tmp_path)

    with pytest.raises(RuntimeError, match="real, aligned observation rows"):
        pipeline.run_inference()

    # Insufficient data must not create a mock forecast cache.
    assert not (tmp_path / "processed" / "latest_forecast.json").exists()
