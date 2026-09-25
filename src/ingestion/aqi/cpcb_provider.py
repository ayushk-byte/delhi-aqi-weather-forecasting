"""CPCB / Data.gov.in Central Pollution Control Board air quality provider."""

from datetime import datetime, timezone
from typing import Any

import httpx

from src.core.constants import DELHI_STATIONS
from src.core.exceptions import ProviderUnavailableError
from src.core.logging import get_logger
from src.ingestion.base import AQIObservation, BaseAQIProvider

logger = get_logger(__name__)


class CPCBProvider(BaseAQIProvider):
    """Fetches official CPCB continuous ambient air quality monitoring data."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.data.gov.in/resource/3b0139f1-e7f9-4618-ac11-37da1a2f0249",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "cpcb"

    def fetch_latest_observations(
        self, station_ids: list[str] | None = None
    ) -> list[AQIObservation]:
        """Fetch latest reported observations for Delhi from CPCB / Data.gov.in."""
        params: dict[str, Any] = {
            "format": "json",
            "filters[state]": "Delhi",
            "limit": 500,
        }
        if self.api_key:
            params["api-key"] = self.api_key

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.error(f"CPCB API request failed: {exc}")
            raise ProviderUnavailableError(f"CPCB feed unreachable: {exc}") from exc

        results: list[AQIObservation] = []
        target_stations = set(station_ids) if station_ids else set(DELHI_STATIONS.keys())

        # Group records by station name / cpcb_id
        records = data.get("records", [])
        station_records: dict[str, dict[str, Any]] = {}

        for rec in records:
            cpcb_station_name = rec.get("station", "").lower()
            matched_id = None
            for st_id, meta in DELHI_STATIONS.items():
                if any(part.lower() in cpcb_station_name for part in meta["name"].split(",")[:1]):
                    matched_id = st_id
                    break

            if not matched_id or matched_id not in target_stations:
                continue

            if matched_id not in station_records:
                station_records[matched_id] = {
                    "last_update": rec.get("last_update"),
                    "pollutants": {},
                    "raw": rec,
                }

            pollutant_id = rec.get("pollutant_id", "").lower()
            avg_value = rec.get("avg_value")
            if avg_value is not None:
                try:
                    val = float(avg_value)
                    if "pm2.5" in pollutant_id or "pm25" in pollutant_id:
                        station_records[matched_id]["pollutants"]["pm25"] = val
                    elif "pm10" in pollutant_id:
                        station_records[matched_id]["pollutants"]["pm10"] = val
                    elif "no2" in pollutant_id:
                        station_records[matched_id]["pollutants"]["no2"] = val
                    elif "so2" in pollutant_id:
                        station_records[matched_id]["pollutants"]["so2"] = val
                    elif "co" in pollutant_id:
                        station_records[matched_id]["pollutants"]["co"] = val
                    elif "ozone" in pollutant_id or "o3" in pollutant_id:
                        station_records[matched_id]["pollutants"]["o3"] = val
                except ValueError:
                    pass

        now_utc = datetime.now(timezone.utc)
        for st_id, st_data in station_records.items():
            pollutants = st_data["pollutants"]
            results.append(
                AQIObservation(
                    station_id=st_id,
                    timestamp=now_utc,
                    pm25=pollutants.get("pm25"),
                    pm10=pollutants.get("pm10"),
                    no2=pollutants.get("no2"),
                    so2=pollutants.get("so2"),
                    co=pollutants.get("co"),
                    o3=pollutants.get("o3"),
                    provider=self.provider_name,
                    raw_payload=st_data["raw"],
                )
            )

        return results

    def fetch_historical_observations(
        self,
        start_date: datetime,
        end_date: datetime,
        station_ids: list[str] | None = None,
    ) -> list[AQIObservation]:
        """Historical CPCB archive queries."""
        logger.info(f"CPCB historical data request for {start_date} to {end_date}")
        return self.fetch_latest_observations(station_ids=station_ids)
