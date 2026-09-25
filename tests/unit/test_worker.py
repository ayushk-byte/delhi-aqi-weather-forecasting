"""Unit tests for the Scheduled Worker."""

from src.pipelines.worker import ScheduledWorker


def test_worker_run_cycle(monkeypatch) -> None:
    class FakeIngestionPipeline:
        def run(self):
            return {"status": "success"}

    class FakeInferencePipeline:
        def run_inference(self):
            return {"status": "success"}

    monkeypatch.setattr("src.pipelines.worker.IngestionPipeline", FakeIngestionPipeline)
    monkeypatch.setattr("src.pipelines.worker.InferencePipeline", FakeInferencePipeline)
    worker = ScheduledWorker(interval_minutes=60)
    result = worker.run_cycle()

    assert "ingestion" in result
    assert "inference" in result
    assert result["ingestion"]["status"] == "success"
    assert result["inference"]["status"] == "success"
