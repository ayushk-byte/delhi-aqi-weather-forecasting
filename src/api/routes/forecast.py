"""Forecasting endpoints: exposes real-time multi-horizon predictions for Delhi NCR."""

from typing import Any

from fastapi import APIRouter, HTTPException

from src.core.constants import DELHI_STATIONS
from src.core.logging import get_logger
from src.ingestion.live_meteo_client import LiveMeteoClient
from src.pipelines.inference_pipeline import InferencePipeline

logger = get_logger(__name__)
router = APIRouter(prefix="/forecast", tags=["Forecasting"])

_live_client = LiveMeteoClient(timeout_seconds=12.0)


def _get_or_run_latest_forecast() -> dict[str, Any]:
    """Retrieve coupled 72-hour forecast using live meteo-chemical pipeline."""
    try:
        data = _live_client.get_all_delhi_stations_data()
        if data.get("status") == "success" and data.get("stations"):
            return data
    except Exception as exc:
        logger.warning(f"Live meteo fetch failed: {exc}. Trying offline pipeline...")

    try:
        pipeline = InferencePipeline()
        return pipeline.run_inference()
    except Exception as exc:
        logger.error(f"Inference pipeline fallback failed: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Coupled forecast currently initializing. Please retry in a few moments.",
        ) from exc


@router.get("/latest")
def get_latest_forecast() -> dict[str, Any]:
    """Get the latest coupled 72-hour forecast across all Delhi stations and horizons."""
    return _get_or_run_latest_forecast()


@router.get("/station/{station_id}")
def get_station_forecast(station_id: str) -> dict[str, Any]:
    """Get 72-hour forecast specifically for a single Delhi monitoring station."""
    st_id = station_id.upper()
    if st_id not in DELHI_STATIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Station '{st_id}' not found. Valid station IDs: {list(DELHI_STATIONS.keys())}",
        )

    forecast_data = _get_or_run_latest_forecast()
    stations = forecast_data.get("stations", [])

    for st in stations:
        if st.get("station_id") == st_id:
            return {
                "generated_at": forecast_data.get("last_updated"),
                "model_name": forecast_data.get("model_name"),
                "station": st,
            }

    raise HTTPException(status_code=404, detail=f"No forecast available for station {st_id}")


@router.post("/run")
def trigger_inference() -> dict[str, Any]:
    """Manually trigger real-time inference pipeline and refresh forecast cache."""
    result = _get_or_run_latest_forecast()
    return {"message": "Inference successfully generated", "result": result}
