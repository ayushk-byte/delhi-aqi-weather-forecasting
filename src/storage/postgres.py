"""PostgreSQL persistence for normalized observations and platform records."""

import os
from pathlib import Path
from typing import Any

from src.core.constants import DELHI_STATIONS

ROOT = Path(__file__).resolve().parents[2]


def _psycopg():
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL storage needs psycopg; run the project setup command to install dependencies."
        ) from exc
    return psycopg, Jsonb


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is required for PostgreSQL storage.")
    return url


def migrate() -> None:
    """Apply the versioned initial schema and structural station reference records."""
    migration = ROOT / "migrations" / "001_initial.sql"
    psycopg, _ = _psycopg()
    with psycopg.connect(database_url(), connect_timeout=5) as connection:
        connection.execute(migration.read_text(encoding="utf-8"), prepare=False)
        for station_id, station in DELHI_STATIONS.items():
            connection.execute(
                """INSERT INTO stations (station_id, name, latitude, longitude, zone, source_id)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (station_id) DO UPDATE SET name=EXCLUDED.name,
                   latitude=EXCLUDED.latitude, longitude=EXCLUDED.longitude,
                   zone=EXCLUDED.zone, source_id=EXCLUDED.source_id""",
                (
                    station_id,
                    station["name"],
                    station["latitude"],
                    station["longitude"],
                    station.get("zone"),
                    station.get("cpcb_id"),
                ),
            )


def persist_air_quality(observations: list[Any]) -> int:
    if not observations:
        return 0
    psycopg, Jsonb = _psycopg()
    rows = [
        (
            observation.station_id,
            observation.timestamp,
            observation.provider,
            observation.pm25,
            observation.pm10,
            observation.no2,
            observation.so2,
            observation.co,
            observation.o3,
            observation.aqi,
            Jsonb(observation.raw_payload),
        )
        for observation in observations
    ]
    with psycopg.connect(database_url(), connect_timeout=5) as connection:
        for source in sorted({row[2] for row in rows}):
            connection.execute(
                "INSERT INTO data_sources (source_id, name, source_type, status, last_success_at) "
                "VALUES (%s, %s, 'air_quality', 'connected', now()) "
                "ON CONFLICT (source_id) DO UPDATE SET status='connected', last_success_at=now()",
                (source, source),
            )
        connection.cursor().executemany(
            """INSERT INTO air_quality_observations
               (station_id, observed_at, source, pm25, pm10, no2, so2, co, o3, aqi, raw_payload)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (station_id, observed_at, source) DO UPDATE SET
               pm25=EXCLUDED.pm25, pm10=EXCLUDED.pm10, no2=EXCLUDED.no2,
               so2=EXCLUDED.so2, co=EXCLUDED.co, o3=EXCLUDED.o3,
               aqi=EXCLUDED.aqi, raw_payload=EXCLUDED.raw_payload""",
            rows,
        )
    return len(rows)


def persist_weather(observation: Any) -> int:
    psycopg, _ = _psycopg()
    with psycopg.connect(database_url(), connect_timeout=5) as connection:
        connection.execute(
            "INSERT INTO data_sources (source_id, name, source_type, status, last_success_at) "
            "VALUES (%s, %s, 'weather', 'connected', now()) "
            "ON CONFLICT (source_id) DO UPDATE SET status='connected', last_success_at=now()",
            (observation.provider, observation.provider),
        )
        connection.execute(
            """INSERT INTO weather_observations
               (latitude, longitude, observed_at, source, temperature_2m,
                relative_humidity_2m, dew_point_2m, surface_pressure, wind_speed_10m,
                wind_direction_10m, wind_gusts_10m, boundary_layer_height, precipitation)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (latitude, longitude, observed_at, source) DO UPDATE SET
               temperature_2m=EXCLUDED.temperature_2m,
               relative_humidity_2m=EXCLUDED.relative_humidity_2m,
               dew_point_2m=EXCLUDED.dew_point_2m,
               surface_pressure=EXCLUDED.surface_pressure,
               wind_speed_10m=EXCLUDED.wind_speed_10m,
               wind_direction_10m=EXCLUDED.wind_direction_10m,
               wind_gusts_10m=EXCLUDED.wind_gusts_10m,
               boundary_layer_height=EXCLUDED.boundary_layer_height,
               precipitation=EXCLUDED.precipitation""",
            (
                observation.latitude,
                observation.longitude,
                observation.timestamp,
                observation.provider,
                observation.temperature_2m,
                observation.relative_humidity_2m,
                observation.dew_point_2m,
                observation.surface_pressure,
                observation.wind_speed_10m,
                observation.wind_direction_10m,
                observation.wind_gusts_10m,
                observation.boundary_layer_height,
                observation.precipitation,
            ),
        )
    return 1


def observation_counts() -> dict[str, int]:
    psycopg, _ = _psycopg()
    with psycopg.connect(database_url(), connect_timeout=5) as connection:
        aqi = connection.execute("SELECT count(*) FROM air_quality_observations").fetchone()[0]
        weather = connection.execute("SELECT count(*) FROM weather_observations").fetchone()[0]
    return {"air_quality": aqi, "weather": weather}


def check_database(url: str | None = None) -> bool:
    psycopg, _ = _psycopg()
    with psycopg.connect(url or database_url(), connect_timeout=2) as connection:
        connection.execute("SELECT 1")
        connection.execute("SELECT count(*) FROM air_quality_observations").fetchone()
        connection.execute("SELECT count(*) FROM weather_observations").fetchone()
    return True


if __name__ == "__main__":
    migrate()
    print("Database schema migration completed.")
