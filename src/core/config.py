"""Configuration management supporting YAML files and environment variable overrides."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StationConfig(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    cpcb_id: str | None = None
    zone: str | None = None


class BoundingBox(BaseModel):
    min_lat: float = 28.35
    max_lat: float = 28.90
    min_lon: float = 76.85
    max_lon: float = 77.40


class IngestionConfig(BaseModel):
    aqi_provider: str = "openaq"
    weather_provider: "str" = "open_meteo"
    poll_interval_minutes: int = 60
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_backoff_seconds: int = 5


class OpenMeteoConfig(BaseModel):
    historical_url: str = "https://archive-api.open-meteo.com/v1/archive"
    forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    hourly_parameters: list[str] = [
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "boundary_layer_height",
        "precipitation",
    ]


class OpenAQConfig(BaseModel):
    base_url: str = "https://api.openaq.org/v3"
    country: str = "IN"
    city: str = "Delhi"
    limit: int = 100


class Settings(BaseSettings):
    """Application-wide settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"

    # API Keys (optional depending on provider)
    openaq_api_key: str | None = None
    data_gov_in_api_key: str | None = None

    # Base paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    data_dir: Path = Path("data")
    raw_aqi_dir: Path = Path("data/raw/aqi")
    raw_weather_dir: Path = Path("data/raw/weather")
    processed_dir: Path = Path("data/processed")
    features_dir: Path = Path("data/features")
    models_dir: Path = Path("models")

    # Ingestion settings
    aqi_provider: str = "openaq"
    weather_provider: str = "open_meteo"
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    open_meteo: OpenMeteoConfig = Field(default_factory=OpenMeteoConfig)
    openaq: OpenAQConfig = Field(default_factory=OpenAQConfig)

    # Horizons & region
    bounding_box: BoundingBox = Field(default_factory=BoundingBox)
    target_pollutants: list[str] = ["pm25", "pm10"]
    horizons_hours: list[int] = [6, 12, 24, 48]

    def resolve_path(self, relative_path: Path | str) -> Path:
        """Resolve a path relative to the project root if it is not absolute."""
        p = Path(relative_path)
        if p.is_absolute():
            return p
        return self.project_root / p


def load_yaml_config(file_path: Path) -> dict[str, Any]:
    """Safely load a YAML config file if it exists."""
    if file_path.is_file():
        with open(file_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


@lru_cache
def get_settings() -> Settings:
    """Factory to retrieve cached application settings."""
    settings = Settings()

    # Attempt to load base_config.yaml and ingestion_config.yaml
    base_cfg_path = settings.project_root / "configs" / "base_config.yaml"
    ingest_cfg_path = settings.project_root / "configs" / "ingestion_config.yaml"

    base_dict = load_yaml_config(base_cfg_path)
    ingest_dict = load_yaml_config(ingest_cfg_path)

    # Override defaults with yaml values if present
    if "forecast" in base_dict:
        if "horizons_hours" in base_dict["forecast"]:
            settings.horizons_hours = base_dict["forecast"]["horizons_hours"]
        if "target_pollutants" in base_dict["forecast"]:
            settings.target_pollutants = base_dict["forecast"]["target_pollutants"]

    if "ingestion" in ingest_dict:
        settings.ingestion = IngestionConfig(**ingest_dict["ingestion"])
        settings.aqi_provider = settings.ingestion.aqi_provider
        settings.weather_provider = settings.ingestion.weather_provider

    if "open_meteo" in ingest_dict:
        settings.open_meteo = OpenMeteoConfig(**ingest_dict["open_meteo"])

    if "openaq" in ingest_dict:
        settings.openaq = OpenAQConfig(**ingest_dict["openaq"])

    return settings
