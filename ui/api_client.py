"""Dashboard API Client with Real-Time Coupled Atmospheric-Chemical Forecaster."""

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from src.core.constants import CPCB_AQI_CATEGORIES, DELHI_STATIONS
from src.core.logging import get_logger
from src.ingestion.live_meteo_client import LiveMeteoClient

logger = get_logger(__name__)


class DashboardAPIClient:
    """Provides real-time observations, 72-hour forecasts, XAI attribution, and alerts for the UI."""

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 6.0) -> None:
        self.base_url = (base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.timeout = timeout_seconds
        self.live_client = LiveMeteoClient(timeout_seconds=12.0)
        self._cached_bundle: dict[str, Any] | None = None

    def is_api_alive(self) -> bool:
        """Check if FastAPI server is responsive."""
        try:
            with httpx.Client(timeout=1.5) as client:
                resp = client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    def get_latest_forecast(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch real-time coupled 72-hour forecast for all Delhi NCR stations."""
        if self._cached_bundle and not force_refresh:
            return self._cached_bundle

        # 1. Try FastAPI backend if online
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/forecast/latest")
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success" and data.get("stations"):
                        self._cached_bundle = data
                        return data
        except Exception:
            pass

        # 2. Seamless in-process live meteo-chemical engine
        try:
            bundle = self.live_client.get_all_delhi_stations_data(force_refresh=force_refresh)
            if bundle.get("status") == "success":
                self._cached_bundle = bundle
                return bundle
        except Exception as exc:
            logger.error(f"Live meteo engine fetch failed: {exc}")

        return {
            "status": "unavailable",
            "reason": "Could not connect to live atmospheric data stream. Check internet connection.",
        }

    def get_current_observations(self) -> list[dict[str, Any]]:
        """Fetch structured current observations across Delhi NCR stations."""
        forecast_bundle = self.get_latest_forecast()
        if forecast_bundle.get("status") != "success":
            return []

        observations = []
        for stn in forecast_bundle.get("stations", []):
            curr = stn.get("current", {})
            observations.append({
                "station_id": stn.get("station_id"),
                "station_name": stn.get("station_name"),
                "cpcb_aqi": curr.get("cpcb_aqi"),
                "aqi_category": curr.get("aqi_category"),
                "dominant_pollutant": curr.get("dominant_pollutant"),
                "pm25": curr.get("pm25"),
                "pm10": curr.get("pm10"),
                "ozone": curr.get("ozone"),
                "no2": curr.get("no2"),
                "temperature_2m": curr.get("temperature_2m"),
                "relative_humidity_2m": curr.get("relative_humidity_2m"),
                "wind_speed_10m": curr.get("wind_speed_10m"),
                "wind_direction_10m": curr.get("wind_direction_10m"),
                "pbl_height_m": curr.get("pbl_height_m"),
                "inversion_category": curr.get("inversion", {}).get("category", "Moderate"),
                "stubble_plume_risk": curr.get("stubble_plume", {}).get("risk", "low"),
                "timestamp": curr.get("timestamp"),
            })
        return observations

    @staticmethod
    def get_explainability(station_data: dict[str, Any], horizon_hours: int = 24) -> dict[str, Any]:
        """Compute feature attribution explaining why AQI is projected to change over this horizon."""
        curr = station_data.get("current", {})
        curr_aqi = float(curr.get("cpcb_aqi") or 120.0)

        # Find snapshot for target horizon
        snapshots = station_data.get("horizon_snapshots", [])
        target_snap = next((s for s in snapshots if s["horizon_hours"] == horizon_hours), snapshots[-1] if snapshots else {})

        pred_aqi = float(target_snap.get("predicted_aqi") or curr_aqi)
        delta_aqi = pred_aqi - curr_aqi

        pbl = float(target_snap.get("pbl_height_m") or 500.0)
        wspd = float(target_snap.get("wind_speed_ms") or 2.5)
        stubble_idx = float(target_snap.get("stubble_plume_index") or 15.0)

        # Inversion capping contribution: low PBL (< 400m) and low wind (< 2.5 m/s)
        inversion_factor = max(0.0, (800.0 - min(800.0, pbl)) / 800.0 * 45.0 + max(0.0, (3.5 - wspd) / 3.5 * 30.0))
        # Stubble smoke contribution
        stubble_factor = stubble_idx * 0.4
        # Local background & traffic accumulation
        background_factor = 25.0

        total_weight = inversion_factor + stubble_factor + background_factor
        inv_pct = round((inversion_factor / total_weight) * 100)
        stub_pct = round((stubble_factor / total_weight) * 100)
        bg_pct = max(5, 100 - inv_pct - stub_pct)

        # Generate human-readable explanation
        if delta_aqi > 15:
            trend = "Deteriorating"
            explanation = (
                f"Air quality is projected to worsen (+{round(delta_aqi)} AQI points) over the next {horizon_hours} hours. "
                f"The primary driver is atmospheric inversion capping ({inv_pct}% contribution) as nocturnal boundary layer "
                f"compresses to {round(pbl)}m with calm winds ({wspd} m/s), trapping particulate accumulation."
            )
            if stub_pct > 25:
                explanation += f" Regional stubble-burning plume advection contributes an estimated {stub_pct}% to this spike."
        elif delta_aqi < -15:
            trend = "Improving"
            explanation = (
                f"Air quality is projected to improve ({round(delta_aqi)} AQI points) over the next {horizon_hours} hours. "
                f"Driven by rising convective boundary layer height ({round(pbl)}m) and increased wind dispersion ({wspd} m/s)."
            )
        else:
            trend = "Stable"
            explanation = (
                f"AQI is forecast to remain relatively steady around {round(pred_aqi)} ({target_snap.get('aqi_category')}). "
                f"Atmospheric ventilation and local emissions remain in equilibrium."
            )

        return {
            "trend": trend,
            "delta_aqi": round(delta_aqi),
            "current_aqi": round(curr_aqi),
            "predicted_aqi": round(pred_aqi),
            "horizon_hours": horizon_hours,
            "explanation": explanation,
            "factors": [
                {"name": "Inversion Cap & Low PBL Height", "percentage": inv_pct, "color": "#E53E3E"},
                {"name": "NW Regional Stubble-Burning Plume", "percentage": stub_pct, "color": "#DD6B20"},
                {"name": "Local Traffic & Urban Emissions", "percentage": bg_pct, "color": "#3182CE"},
            ],
        }

    @staticmethod
    def get_forecast_alerts(station_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate CPCB-standard forecast-based early warnings and health advisories."""
        alerts = []
        snapshots = station_data.get("horizon_snapshots", [])

        # Find maximum predicted AQI across 72 hours
        max_snap = max(snapshots, key=lambda s: s.get("predicted_aqi", 0)) if snapshots else {}
        max_aqi = max_snap.get("predicted_aqi", 0)
        max_cat = max_snap.get("aqi_category", "Moderate")
        max_h = max_snap.get("horizon_hours", 24)

        if max_aqi >= 401:
            alerts.append({
                "severity": "CRITICAL",
                "badge": "🚨 Severe AQI Alert (400+)",
                "title": f"Projected Severe Episode in +{max_h} Hours",
                "message": (
                    f"Forecast predicts AQI reaching {max_aqi} ({max_cat}). "
                    "Extreme atmospheric stagnation with severe boundary layer collapse."
                ),
                "advisories": [
                    "Vulnerable individuals (children, elderly, respiratory/cardiac patients) should stay strictly indoors.",
                    "Avoid all outdoor physical exertion and sports.",
                    "Use certified N95/N99 respirators if outdoor movement is unavoidable.",
                    "Industrial dust control and GRAP Stage IV emergency guidelines recommended.",
                ],
                "color": "#7E0023",
            })
        elif max_aqi >= 301:
            alerts.append({
                "severity": "WARNING",
                "badge": "⚠️ Very Poor AQI Warning",
                "title": f"High Pollution Expected in +{max_h} Hours",
                "message": (
                    f"Forecast indicates AQI will peak at {max_aqi} ({max_cat}). "
                    "Prolonged exposure may cause respiratory distress."
                ),
                "advisories": [
                    "Sensitive groups should avoid prolonged outdoor exposure.",
                    "Wear masks during morning and late evening inversion peaks.",
                    "Keep indoor air purifiers active and windows closed during peak stagnation hours.",
                ],
                "color": "#660099",
            })
        elif max_aqi >= 201:
            alerts.append({
                "severity": "ADVISORY",
                "badge": "📢 Poor Air Quality Advisory",
                "title": f"Moderate Deterioration Expected (+{max_h}h)",
                "message": f"AQI projected to reach {max_aqi} ({max_cat}). May cause breathing discomfort to sensitive people.",
                "advisories": [
                    "Limit intense outdoor exercise during early mornings.",
                    "Ensure adequate hydration and monitor local station trends.",
                ],
                "color": "#CC0033",
            })
        else:
            alerts.append({
                "severity": "NORMAL",
                "badge": "✅ Favorable Dispersive Conditions",
                "title": "Air Quality Within Manageable Limits",
                "message": f"72-hour maximum AQI is {max_aqi} ({max_cat}). Adequate atmospheric ventilation is active.",
                "advisories": [
                    "Normal outdoor activities can proceed.",
                    "Ventilation and air quality remain within acceptable thresholds.",
                ],
                "color": "#009966",
            })

        return alerts
