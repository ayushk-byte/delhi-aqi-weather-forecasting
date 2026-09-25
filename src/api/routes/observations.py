"""Observation endpoints: returns station directory and current air quality / weather readings."""

from typing import Any

from fastapi import APIRouter

from src.core.constants import DELHI_STATIONS
from src.ingestion.live_meteo_client import LiveMeteoClient

router = APIRouter(prefix="/observations", tags=["Observations"])
api_router = APIRouter(tags=["Current observations"])

_live_client = LiveMeteoClient(timeout_seconds=12.0)


@router.get("/stations")
def get_stations() -> list[dict[str, Any]]:
    """Return directory of all reference monitoring stations in Delhi NCR."""
    stations = []
    for st_id, meta in DELHI_STATIONS.items():
        stations.append(
            {
                "station_id": st_id,
                "name": meta["name"],
                "latitude": meta["latitude"],
                "longitude": meta["longitude"],
                "cpcb_id": meta.get("cpcb_id"),
                "zone": meta.get("zone"),
            }
        )
    return stations


@router.get("/current")
def get_current_observations() -> list[dict[str, Any]]:
    """Return real-time observations across all Delhi NCR monitoring stations."""
    bundle = _live_client.get_all_delhi_stations_data()
    results = []
    for stn in bundle.get("stations", []):
        curr = stn.get("current", {})
        results.append({
            "station_id": stn.get("station_id"),
            "station_name": stn.get("station_name"),
            "latitude": stn.get("latitude"),
            "longitude": stn.get("longitude"),
            "timestamp": curr.get("timestamp"),
            "source": "open_meteo_cpcb_harmonized",
            "data_type": "observed_realtime",
            "pm25": curr.get("pm25"),
            "pm10": curr.get("pm10"),
            "o3": curr.get("ozone"),
            "no2": curr.get("no2"),
            "so2": curr.get("so2"),
            "co": curr.get("co"),
            "cpcb_aqi": curr.get("cpcb_aqi"),
            "aqi_category": curr.get("aqi_category"),
            "temperature_2m": curr.get("temperature_2m"),
            "relative_humidity_2m": curr.get("relative_humidity_2m"),
            "wind_speed_10m": curr.get("wind_speed_10m"),
            "wind_direction_10m": curr.get("wind_direction_10m"),
            "pbl_height_m": curr.get("pbl_height_m"),
            "inversion_category": curr.get("inversion", {}).get("category"),
            "stubble_plume_risk": curr.get("stubble_plume", {}).get("status"),
        })
    return results


@api_router.get("/api/air-quality/current")
def get_current_air_quality() -> list[dict[str, Any]]:
    """Return latest real station pollutant measurements and their AQI derivation."""
    return get_current_observations()


@api_router.get("/api/weather/current")
def get_current_weather() -> dict[str, Any]:
    """Return current regional weather observation for Delhi NCR."""
    observations = get_current_observations()
    if observations:
        sample = observations[0]
        return {
            "timestamp": sample.get("timestamp"),
            "temperature_2m": sample.get("temperature_2m"),
            "relative_humidity_2m": sample.get("relative_humidity_2m"),
            "wind_speed_10m": sample.get("wind_speed_10m"),
            "wind_direction_10m": sample.get("wind_direction_10m"),
            "pbl_height_m": sample.get("pbl_height_m"),
            "data_type": "observed_realtime",
        }
    return {"status": "unavailable", "observation": None}
