"""FastAPI entrypoint for Delhi NCR Air Pollution-Weather Coupled Forecasting System."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.forecast import router as forecast_router
from src.api.routes.health import router as health_router
from src.api.routes.observations import api_router as live_observations_router
from src.api.routes.observations import router as obs_router

app = FastAPI(
    title="Delhi NCR AQI-Weather Coupled Forecasting API",
    description=(
        "Production REST API for multi-horizon air pollution forecasting coupled with "
        "atmospheric dispersion and numerical weather predictions."
    ),
    version="0.1.0",
)

# Enable CORS for local dashboards and external consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route controllers
app.include_router(health_router)
app.include_router(forecast_router)
app.include_router(obs_router)
app.include_router(live_observations_router)


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    return {
        "project": "Delhi NCR Air Pollution-Weather Coupled Forecasting System",
        "version": "0.1.0",
        "docs_url": "/docs",
        "health_url": "/health",
    }
