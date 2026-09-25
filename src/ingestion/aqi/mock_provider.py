"""Mock AQI provider generating realistic, physically consistent air quality data for Delhi stations."""

import math
from datetime import datetime, timedelta, timezone

from src.core.constants import DELHI_STATIONS
from src.ingestion.base import AQIObservation, BaseAQIProvider


class MockAQIProvider(BaseAQIProvider):
    """Generates synthetic Delhi air pollution observations matching known diurnal patterns."""

    def __init__(self, base_pm25: float = 120.0, seed: int = 42) -> None:
        self._base_pm25 = base_pm25
        self._seed = seed

    @property
    def provider_name(self) -> str:
        return "mock_aqi"

    def _generate_synthetic_point(self, station_id: str, dt: datetime) -> AQIObservation:
        # Delhi diurnal pollution cycle:
        # Peak 1: 08:00 - 10:00 (morning traffic + shallow PBL)
        # Trough: 14:00 - 16:00 (maximum vertical mixing)
        # Peak 2: 21:00 - 23:00 (evening traffic + nocturnal inversion)
        hour = dt.hour + dt.minute / 60.0
        diurnal_factor = 1.0 + 0.45 * math.cos((hour - 8.0) * 2 * math.pi / 24.0)

        # Station-specific spatial offset
        station_bias = (hash(station_id) % 30) - 15.0

        # Pseudo-random noise
        pseudo_noise = math.sin((dt.timestamp() % 86400) / 1000.0) * 8.0

        pm25 = max(10.0, (self._base_pm25 + station_bias) * diurnal_factor + pseudo_noise)
        pm10 = pm25 * 1.8 + 15.0
        no2 = max(5.0, pm25 * 0.35 + 10.0)
        so2 = max(2.0, pm25 * 0.10 + 4.0)
        co = round(max(0.2, pm25 * 0.015), 2)
        o3 = max(5.0, 45.0 - (pm25 * 0.15))

        return AQIObservation(
            station_id=station_id,
            timestamp=dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc),
            pm25=round(pm25, 2),
            pm10=round(pm10, 2),
            no2=round(no2, 2),
            so2=round(so2, 2),
            co=co,
            o3=round(o3, 2),
            provider=self.provider_name,
            raw_payload={"mock": True, "generated_at": datetime.now(timezone.utc).isoformat()},
        )

    def fetch_latest_observations(
        self, station_ids: list[str] | None = None
    ) -> list[AQIObservation]:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        stations = station_ids if station_ids else list(DELHI_STATIONS.keys())
        return [self._generate_synthetic_point(st_id, now) for st_id in stations]

    def fetch_historical_observations(
        self,
        start_date: datetime,
        end_date: datetime,
        station_ids: list[str] | None = None,
    ) -> list[AQIObservation]:
        stations = station_ids if station_ids else list(DELHI_STATIONS.keys())
        observations: list[AQIObservation] = []
        current = start_date
        while current <= end_date:
            for st_id in stations:
                observations.append(self._generate_synthetic_point(st_id, current))
            current += timedelta(hours=1)
        return observations
