"""Unit tests for FastAPI endpoints."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "project" in data
    assert "docs_url" in data


def test_health_endpoint() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "champion_models" in data


def test_observations_stations() -> None:
    resp = client.get("/observations/stations")
    assert resp.status_code == 200
    stations = resp.json()
    assert len(stations) >= 8
    station_ids = [s["station_id"] for s in stations]
    assert "DL001" in station_ids


def test_observations_current() -> None:
    resp = client.get("/observations/current")
    assert resp.status_code == 200
    obs = resp.json()
    assert isinstance(obs, list)
    if obs:
        assert "station_id" in obs[0]
        assert "pm25" in obs[0]


def test_forecast_latest_reports_unavailable_without_real_history(monkeypatch) -> None:
    from src.pipelines.inference_pipeline import InferencePipeline

    monkeypatch.setattr(
        InferencePipeline,
        "run_inference",
        lambda self: (_ for _ in ()).throw(RuntimeError("no real history")),
    )
    resp = client.get("/forecast/latest")
    assert resp.status_code == 503
    assert "Forecast unavailable" in resp.json()["detail"]


def test_forecast_station_valid_reports_unavailable_without_real_history(monkeypatch) -> None:
    from src.pipelines.inference_pipeline import InferencePipeline

    monkeypatch.setattr(
        InferencePipeline,
        "run_inference",
        lambda self: (_ for _ in ()).throw(RuntimeError("no real history")),
    )
    resp = client.get("/forecast/station/DL001")
    assert resp.status_code == 503


def test_forecast_station_invalid() -> None:
    resp = client.get("/forecast/station/INVALID_STATION_ID")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_forecast_run_reports_unavailable_without_real_history(monkeypatch) -> None:
    from src.pipelines.inference_pipeline import InferencePipeline

    monkeypatch.setattr(
        InferencePipeline,
        "run_inference",
        lambda self: (_ for _ in ()).throw(RuntimeError("no real history")),
    )
    resp = client.post("/forecast/run")
    assert resp.status_code == 503
