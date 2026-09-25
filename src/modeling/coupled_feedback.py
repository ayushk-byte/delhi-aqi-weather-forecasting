"""Coupled Weather-Chemistry Feedback Engine for Delhi NCR.

Implements:
1. Atmospheric Inversion Strength Index (ISI) & Boundary Layer Capping.
2. Aerosol-Radiation Feedback (Solar Dimming & Secondary PBL Suppression).
3. Regional Stubble-Burning Plume Transport & Advection from the NW Agricultural Corridor.
4. Photochemical Ground-Level Ozone (O3) and NO2 Coupling.
"""

import math
from typing import Any


class AtmosphericFeedbackEngine:
    """Simulates dynamic two-way feedback between atmospheric physics and chemical transport."""

    @staticmethod
    def calculate_inversion_index(
        pbl_height: float,
        wind_speed: float,
        temperature: float,
        relative_humidity: float,
    ) -> dict[str, Any]:
        """Compute the Atmospheric Inversion Strength Index (0 to 100).

        A strong inversion occurs when the Planetary Boundary Layer (PBL) collapses
        (especially <300m at night/early morning) and surface wind speeds are low (<2 m/s),
        trapping smoke and particulates near the surface.
        """
        # PBL compression score: 0 (well-mixed > 1500m) to 60 (compressed < 150m)
        pbl_clamped = max(50.0, min(2000.0, pbl_height))
        if pbl_clamped <= 150.0:
            pbl_score = 60.0
        elif pbl_clamped >= 1200.0:
            pbl_score = 0.0
        else:
            pbl_score = ((1200.0 - pbl_clamped) / (1200.0 - 150.0)) * 60.0

        # Wind stagnation score: 0 (strong winds > 6 m/s) to 30 (calm < 1 m/s)
        wind_clamped = max(0.2, min(8.0, wind_speed))
        if wind_clamped >= 6.0:
            wind_score = 0.0
        elif wind_clamped <= 1.0:
            wind_score = 30.0
        else:
            wind_score = ((6.0 - wind_clamped) / 5.0) * 30.0

        # Humidity/condensation multiplier score: 0 to 10
        rh_score = (max(30.0, min(100.0, relative_humidity)) - 30.0) / 70.0 * 10.0

        inversion_index = round(min(100.0, max(0.0, pbl_score + wind_score + rh_score)), 1)

        if inversion_index >= 70.0:
            category = "Severe Inversion Cap"
            severity = "critical"
            description = (
                f"Severe atmospheric capping (PBLH: {round(pbl_height)}m, Wind: {round(wind_speed, 1)} m/s). "
                "Dispersal is suppressed; severe particulate accumulation expected."
            )
        elif inversion_index >= 45.0:
            category = "Moderate Inversion"
            severity = "warning"
            description = (
                f"Moderate thermal inversion present (PBLH: {round(pbl_height)}m). "
                "Partial vertical trapping with restricted morning dispersion."
            )
        else:
            category = "Well-Mixed Atmosphere"
            severity = "favorable"
            description = (
                f"Well-mixed convective boundary layer (PBLH: {round(pbl_height)}m, Wind: {round(wind_speed, 1)} m/s). "
                "Atmospheric ventilation is actively dispersing pollutants."
            )

        return {
            "inversion_index": inversion_index,
            "category": category,
            "severity": severity,
            "pbl_height_m": round(pbl_height, 1),
            "wind_speed_ms": round(wind_speed, 1),
            "description": description,
        }

    @staticmethod
    def calculate_stubble_plume_advection(
        wind_direction_deg: float,
        wind_speed_ms: float,
        inversion_index: float,
    ) -> dict[str, Any]:
        """Estimate regional stubble-burning plume advection from the NW corridor (Punjab/Haryana).

        The agricultural burning corridor lies primarily to the North-West of Delhi (290° to 335°).
        Moderate winds from this direction carry dense smoke plumes directly into the Delhi bowl,
        where thermal inversions subsequently trap them.
        """
        # Target NW corridor center is ~315 degrees
        target_dir = 315.0
        diff = abs(wind_direction_deg - target_dir)
        if diff > 180.0:
            diff = 360.0 - diff

        is_nw_corridor = diff <= 45.0

        if is_nw_corridor:
            # Maximum alignment when directly 315°
            alignment_factor = math.cos(math.radians(diff * 2))  # 1.0 down to ~0.0
            alignment_factor = max(0.0, alignment_factor)

            # Wind speed sweet-spot: 2.0 to 6.5 m/s brings smoke without blowing it away instantly
            if 2.0 <= wind_speed_ms <= 6.5:
                transport_factor = 1.0
            elif wind_speed_ms < 2.0:
                transport_factor = wind_speed_ms / 2.0
            else:
                transport_factor = max(0.3, 1.0 - (wind_speed_ms - 6.5) / 5.0)

            # Inversion trapping acts as a multiplier
            trap_multiplier = 0.5 + (inversion_index / 200.0)

            raw_index = alignment_factor * transport_factor * trap_multiplier * 100.0
            plume_index = round(min(100.0, max(0.0, raw_index)), 1)
        else:
            plume_index = round(max(0.0, (1.0 - diff / 180.0) * 15.0), 1)

        if plume_index >= 65.0:
            status = "High Regional Influx"
            risk = "high"
            summary = (
                f"Prevailing North-Westerly winds ({round(wind_direction_deg)}° at {round(wind_speed_ms, 1)} m/s) "
                "channeling agricultural smoke plumes into Delhi with active inversion trapping."
            )
        elif plume_index >= 35.0:
            status = "Moderate Regional Advection"
            risk = "moderate"
            summary = (
                f"Partial NW wind alignment ({round(wind_direction_deg)}°). Regional biomass smoke "
                "is contributing moderately to ambient particulate loading."
            )
        else:
            status = "Low / Dispersed Corridor"
            risk = "low"
            summary = (
                f"Wind flow ({round(wind_direction_deg)}°) is not strongly aligned with the NW stubble-burning "
                "corridor, minimizing cross-border biomass smoke transport."
            )

        return {
            "plume_index": plume_index,
            "status": status,
            "risk": risk,
            "wind_direction_deg": round(wind_direction_deg, 1),
            "wind_speed_ms": round(wind_speed_ms, 1),
            "summary": summary,
        }

    @staticmethod
    def simulate_aerosol_radiation_feedback(
        pm25_concentration: float,
        base_pbl_height: float,
        temperature_2m: float,
    ) -> dict[str, Any]:
        """Simulate two-way aerosol-radiation feedback.

        Dense PM2.5 aerosol layers scatter incoming solar radiation (solar dimming),
        cooling the ground by 0.5°C - 2.5°C during the day. This cools the surface air,
        dampens thermal convection, and compresses the boundary layer height (PBLH)
        by 10% to 35%, which further increases pollutant concentrations.
        """
        # Attenuation factor based on PM2.5 loading
        pm_clamped = max(0.0, pm25_concentration)

        # Solar dimming cooling estimate (up to -2.8 deg C at 500 ug/m3)
        temp_depression = round(min(2.8, (pm_clamped / 500.0) * 2.2), 2)

        # PBL suppression ratio (up to 32% compression)
        pbl_suppression_pct = round(min(32.0, (pm_clamped / 400.0) * 25.0), 1)
        effective_pbl_height = round(base_pbl_height * (1.0 - (pbl_suppression_pct / 100.0)), 1)

        # Feedback-amplified PM2.5 (trapping effect)
        feedback_pm25_boost = round(pm_clamped * (1.0 + (pbl_suppression_pct / 180.0)), 1)

        return {
            "temperature_depression_deg_c": temp_depression,
            "pbl_suppression_pct": pbl_suppression_pct,
            "base_pbl_height_m": round(base_pbl_height, 1),
            "effective_pbl_height_m": effective_pbl_height,
            "feedback_amplified_pm25": feedback_pm25_boost,
            "active_feedback": pm_clamped > 90.0,
        }
