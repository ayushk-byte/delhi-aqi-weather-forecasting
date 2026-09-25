"""Health check and service status route."""

import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter

from src.core.config import get_settings
from src.core.constants import DELHI_STATIONS
from src.ingestion import get_aqi_provider, get_weather_provider
from src.modeling.registry import ModelRegistry

router = APIRouter(tags=["Health"])


def _database_check(url: str) -> str:
    try:
        from src.storage.postgres import check_database

        check_database(url)
        return "connected"
    except Exception:
        return "unavailable"


def _redis_check(host: str, port: int) -> str:
    try:
        with socket.create_connection((host, port), timeout=1.5) as connection:
            connection.sendall(b"*1\r\n$4\r\nPING\r\n")
            if b"PONG" not in connection.recv(32):
                return "unavailable"
        return "connected"
    except OSError:
        return "unavailable"


def _latest_observation(subdir: str) -> str | None:
    root = get_settings().resolve_path(Path("data/raw") / subdir)
    files = (
        sorted(root.rglob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if root.exists()
        else []
    )
    for file in files:
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
            if isinstance(payload, list) and payload:
                live = [
                    row
                    for row in payload
                    if not str(row.get("provider", "")).lower().startswith("mock")
                ]
                return live[0].get("timestamp") if live else None
            if isinstance(payload, dict):
                center = payload.get("center", {})
                current = center.get("current", {})
                if str(current.get("provider", "")).lower().startswith("mock"):
                    continue
                return current.get("timestamp") or payload.get("ingested_at")
        except (OSError, ValueError, AttributeError):
            continue
    return None


def _provider_check(provider, check):
    try:
        result = check(provider)
        if result is False:
            return "unavailable"
        return "connected"
    except Exception:
        return "unavailable"


def _freshness(timestamp: str | None) -> str:
    if not timestamp:
        return "UNAVAILABLE"
    try:
        observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        age_minutes = max(0, (datetime.now(timezone.utc) - observed).total_seconds() / 60)
    except ValueError:
        return "UNAVAILABLE"
    if age_minutes < int(os.getenv("DATA_FRESH_LIVE_MINUTES", "15")):
        return "LIVE"
    if age_minutes <= int(os.getenv("DATA_FRESH_RECENT_MINUTES", "60")):
        return "RECENT"
    return "STALE"


def _system_health() -> dict:
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aqi")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis = urlparse(redis_url)
    database = _database_check(db_url)
    redis_status = _redis_check(redis.hostname or "localhost", redis.port or 6379)
    weather_provider, aqi_provider = get_weather_provider(), get_aqi_provider()
    for provider in (weather_provider, aqi_provider):
        if hasattr(provider, "timeout_seconds"):
            provider.timeout_seconds = min(provider.timeout_seconds, 5.0)
    station = next(iter(DELHI_STATIONS.values()))
    weather = _provider_check(
        weather_provider,
        lambda p: (
            p.fetch_current_weather(station["latitude"], station["longitude"]).temperature_2m
            is not None
        ),
    )
    air_quality = _provider_check(aqi_provider, lambda p: bool(p.fetch_latest_observations()))
    latest_weather = _latest_observation("weather")
    latest_aqi = _latest_observation("aqi")
    weather_freshness = _freshness(latest_weather)
    air_quality_freshness = _freshness(latest_aqi)
    try:
        model = ModelRegistry().get_champion_model("pm25").name
    except Exception:
        model = "development"
    checks = [database, redis_status, weather, air_quality]
    return {
        "status": (
            "healthy"
            if all(x == "connected" for x in checks)
            and weather_freshness in ("LIVE", "RECENT")
            and air_quality_freshness in ("LIVE", "RECENT")
            else "degraded"
        ),
        "database": database,
        "redis": redis_status,
        "weather_api": weather,
        "air_quality_api": air_quality,
        "latest_weather_observation": latest_weather,
        "weather_freshness": weather_freshness,
        "latest_air_quality_observation": latest_aqi,
        "air_quality_freshness": air_quality_freshness,
        "forecast_model": model,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health")
def healthcheck() -> dict:
    """Return system liveness, active environment, and registered champion models."""
    settings = get_settings()
    registry = ModelRegistry()

    try:
        champion_pm25 = registry.get_champion_model("pm25").name
    except Exception:
        champion_pm25 = "unavailable"

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.environment,
        "version": "0.1.0",
        "champion_models": {
            "pm25": champion_pm25,
        },
    }


@router.get("/api/system/health")
@router.get("/api/system/status")
def system_health() -> dict:
    """Check configured providers and local infrastructure; never invent live status."""
    return _system_health()
