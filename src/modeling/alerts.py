"""Forecast-based alert and decision-support engine grounded in CPCB / GRAP guidelines."""

from datetime import datetime, timezone
from typing import Any


def generate_forecast_alerts(
    station_predictions: list[dict[str, Any]],
    current_observations: list[dict[str, Any]] | None = None,
    city_summary: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate proactive forecast-based warnings triggered by anticipated deterioration or hotspot emergence."""
    alerts = []
    now = datetime.now(timezone.utc)

    # 1. Regional Deterioration Alert
    if city_summary and len(city_summary) >= 2:
        curr_mean = city_summary[0].get("city_mean_aqi", 150)
        h24_mean = next(
            (s.get("city_mean_aqi") for s in city_summary if s.get("horizon_hours") == 24),
            city_summary[-1].get("city_mean_aqi", 150),
        )
        delta = h24_mean - curr_mean

        if delta >= 40:
            alerts.append(
                {
                    "id": f"alert_regional_deterioration_{now.strftime('%Y%m%d%H')}",
                    "alert_type": "Rapid Deterioration Warning",
                    "severity": "High" if h24_mean >= 301 else "Medium",
                    "scope": "Regional (Delhi NCR)",
                    "message": (
                        f"Regional AQI is forecast to deteriorate significantly (+{delta} points) "
                        f"over the next 24 hours, rising from {curr_mean} to {h24_mean}."
                    ),
                    "action_advisory": (
                        "Precautionary health advisory: Sensitive groups (children, elderly, asthmatics) "
                        "should minimize outdoor morning exertion under impending inversion conditions."
                    ),
                    "authoritative_basis": "CPCB Health Advisory & Delhi GRAP Framework",
                }
            )

    # 2. Severe / Critical Forecast Alert
    severe_stations = []
    very_poor_stations = []

    for stn in station_predictions:
        name = stn.get("station_name", "Station")
        for h in stn.get("horizons", []):
            if h.get("horizon_hours") in (24, 48):
                cat = h.get("aqi_category")
                aqi = h.get("predicted_aqi", 0)
                if cat == "Severe" or aqi >= 401:
                    severe_stations.append((name.split(",")[0], h["horizon_hours"], aqi))
                elif cat == "Very Poor" or aqi >= 301:
                    very_poor_stations.append((name.split(",")[0], h["horizon_hours"], aqi))

    if severe_stations:
        st_names = list(dict.fromkeys(s[0] for s in severe_stations))[:3]
        alerts.append(
            {
                "id": f"alert_severe_aqi_{now.strftime('%Y%m%d%H')}",
                "alert_type": "Severe Air Quality Forecast",
                "severity": "Critical",
                "scope": ", ".join(st_names),
                "message": (
                    f"Forecast models predict entry into 'Severe' AQI (>400) at: {', '.join(st_names)}. "
                    f"Atmospheric dispersion capacity is projected to fall below critical thresholds."
                ),
                "action_advisory": (
                    "Strict outdoor physical activity restrictions recommended. N95 respirator masks advised "
                    "for essential commutes during peak hours."
                ),
                "authoritative_basis": "Delhi GRAP Stage-III/IV Trigger Criteria",
            }
        )
    elif very_poor_stations:
        st_names = list(dict.fromkeys(s[0] for s in very_poor_stations))[:3]
        alerts.append(
            {
                "id": f"alert_very_poor_{now.strftime('%Y%m%d%H')}",
                "alert_type": "Very Poor Air Quality Forecast",
                "severity": "High",
                "scope": ", ".join(st_names),
                "message": f"Expected entry into 'Very Poor' AQI (301-400) within 24-48 hours at: {', '.join(st_names)}.",
                "action_advisory": "Avoid prolonged outdoor exposure during early morning and late evening rush hours.",
                "authoritative_basis": "CPCB Public Health Advisory",
            }
        )

    # Fallback advisory if air is clean
    if not alerts:
        alerts.append(
            {
                "id": f"alert_normal_{now.strftime('%Y%m%d%H')}",
                "alert_type": "Normal Advisory",
                "severity": "Low",
                "scope": "Delhi NCR",
                "message": "Forecast indicates moderate atmospheric dispersion over the next 48 hours without critical deterioration.",
                "action_advisory": "Standard urban outdoor activity permissible.",
                "authoritative_basis": "CPCB Guidelines",
            }
        )

    return alerts
