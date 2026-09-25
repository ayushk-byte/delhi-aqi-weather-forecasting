"""OpenAQ API Provider for live Delhi air quality observations."""

import math
from datetime import datetime, timezone

import httpx

from src.core.constants import DELHI_STATIONS, PHYSICAL_BOUNDS
from src.core.exceptions import ProviderUnavailableError
from src.core.logging import get_logger
from src.ingestion.base import AQIObservation, BaseAQIProvider

logger = get_logger(__name__)


class OpenAQProvider(BaseAQIProvider):
    """Fetches real-time and historical air quality data from OpenAQ v3 API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openaq.org/v3",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "openaq"

    def _get_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _match_nearest_station(self, lat: float, lon: float) -> str | None:
        """Find the nearest internal Delhi station within 10km."""
        best_id = None
        min_dist = float("inf")
        for st_id, meta in DELHI_STATIONS.items():
            dlat = math.radians(meta["latitude"] - lat)
            dlon = math.radians(meta["longitude"] - lon)
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(math.radians(lat))
                * math.cos(math.radians(meta["latitude"]))
                * math.sin(dlon / 2) ** 2
            )
            dist_km = 6371 * 2 * math.asin(math.sqrt(a))
            if dist_km < min_dist:
                min_dist = dist_km
                best_id = st_id
        return best_id if min_dist <= 15.0 else None

    def fetch_latest_observations(
        self, station_ids: list[str] | None = None
    ) -> list[AQIObservation]:
        """Fetch latest air quality measurements around Delhi NCR."""
        url = f"{self.base_url}/locations"
        params = {
            "bbox": "76.85,28.35,77.40,28.90",
            "limit": 100,
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.get(url, params=params, headers=self._get_headers())
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.error(f"OpenAQ latest observations failed: {exc}")
            raise ProviderUnavailableError(f"OpenAQ request failed: {exc}") from exc

        results: dict[str, AQIObservation] = {}
        target_stations = set(station_ids) if station_ids else set(DELHI_STATIONS.keys())

        for loc in data.get("results", []):
            coords = loc.get("coordinates", {})
            lat = coords.get("latitude")
            lon = coords.get("longitude")
            if lat is None or lon is None:
                continue

            matched_id = self._match_nearest_station(lat, lon)
            if not matched_id or matched_id not in target_stations:
                continue
            if matched_id in results:
                continue

            sensor_parameters = {
                sensor.get("id"): sensor.get("parameter", {}) for sensor in loc.get("sensors", [])
            }
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.get(
                        f"{self.base_url}/locations/{loc['id']}/latest",
                        params={"limit": 100},
                        headers=self._get_headers(),
                    )
                    response.raise_for_status()
                    latest_data = response.json()
            except Exception as exc:
                logger.warning("OpenAQ latest failed for location %s: %s", loc.get("id"), exc)
                continue

            timestamped_values: list[tuple[str, float, datetime]] = []
            latest_dt: datetime | None = None
            for measurement in latest_data.get("results", []):
                parameter = sensor_parameters.get(measurement.get("sensorsId"), {})
                pollutant = self._pollutant_name(parameter.get("name", ""))
                if pollutant is None or measurement.get("value") is None:
                    continue
                try:
                    value = self._normalize_value(
                        pollutant, float(measurement["value"]), parameter.get("units", "")
                    )
                except (TypeError, ValueError):
                    continue
                minimum, maximum = PHYSICAL_BOUNDS.get(
                    pollutant, (0.0, 1000.0 if pollutant == "o3" else float("inf"))
                )
                if not minimum <= value <= maximum:
                    logger.warning("Rejecting out-of-range %s reading from OpenAQ", pollutant)
                    continue
                timestamp_value = measurement.get("datetime")
                timestamp_str = (
                    timestamp_value.get("utc")
                    if isinstance(timestamp_value, dict)
                    else timestamp_value
                )
                if timestamp_str:
                    try:
                        parsed = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        timestamped_values.append((pollutant, value, parsed))
                        if latest_dt is None or parsed > latest_dt:
                            latest_dt = parsed
                    except ValueError:
                        continue

            if not timestamped_values or latest_dt is None:
                continue
            # One record has one timestamp: omit older parameter readings instead of
            # displaying them as though they were observed at the newest parameter time.
            values = {
                pollutant: value
                for pollutant, value, timestamp in timestamped_values
                if timestamp == latest_dt
            }
            observation = AQIObservation(
                station_id=matched_id,
                timestamp=latest_dt,
                **values,
                provider=self.provider_name,
                raw_payload={"location": loc, "latest": latest_data},
            )
            previous = results.get(matched_id)
            if previous is None or observation.timestamp > previous.timestamp:
                results[matched_id] = observation

        return list(results.values())

    @staticmethod
    def _pollutant_name(name: str) -> str | None:
        normalized = name.lower().replace(".", "")
        for pollutant in ("pm25", "pm10", "no2", "so2", "co", "o3"):
            if pollutant in normalized or (pollutant == "pm25" and "pm2.5" in name.lower()):
                return pollutant
        return None

    @staticmethod
    def _normalize_value(pollutant: str, value: float, units: str) -> float:
        """Normalize common OpenAQ units into the project schema units."""
        unit = units.lower().replace("µ", "u").replace("μ", "u").replace("³", "3")
        unit = unit.replace(" ", "").replace("/", "")
        molecular_weight = {"no2": 46.0055, "so2": 64.066, "o3": 48.0, "co": 28.01}
        if pollutant in ("pm25", "pm10"):
            if unit in ("mgm3", "mgm-3"):
                return value * 1000.0
            return value
        if pollutant == "co":
            if unit in ("ppm", "ppmv"):
                return value * molecular_weight[pollutant] / 24.45
            if unit in ("ugm3", "ugm-3"):
                return value / 1000.0
            return value
        if unit in ("ppm", "ppmv"):
            return value * molecular_weight[pollutant] * 1000.0 / 24.45
        if unit in ("ppb", "ppbv"):
            return value * molecular_weight[pollutant] / 24.45
        if unit in ("mgm3", "mgm-3"):
            return value * 1000.0
        return value

    def fetch_historical_observations(
        self,
        start_date: datetime,
        end_date: datetime,
        station_ids: list[str] | None = None,
    ) -> list[AQIObservation]:
        """Historical retrieval is not yet implemented; never relabel latest as history."""
        raise ProviderUnavailableError(
            "OpenAQ historical ingestion is not implemented; refusing to substitute latest data."
        )
