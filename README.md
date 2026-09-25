# Delhi NCR Air Pollution–Weather Coupled Forecasting System

[![CI Pipeline](https://github.com/ayushk-byte/delhi-aqi-weather-forecasting/actions/workflows/ci.yml/badge.svg)](https://github.com/ayushk-byte/delhi-aqi-weather-forecasting/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A production-grade, weather-aware air quality forecasting system designed specifically for the unique atmospheric physics of the **Delhi National Capital Region (NCR)**.

The system couples real-time air pollution measurements ($\text{PM}_{2.5}, \text{PM}_{10}, \text{NO}_2, \text{SO}_2, \text{CO}$) with numerical weather predictions (NWP) to forecast particulate concentrations and official **CPCB Indian National Air Quality Index (IND-AQI)** across multi-hour horizons: **+6h, +12h, +24h, and +48h**.

---

## 🏛️ System Architecture

```text
[ Live AQI Feeds ]       [ Weather APIs / NWP Forecasts ]
(OpenAQ / CPCB / Mock)    (Open-Meteo / ECMWF / Mock)
          │                              │
          ▼                              ▼
  ┌──────────────────────────────────────────────┐
  │         1. Pluggable Ingestion Layer         │
  │   - BaseAQIProvider / BaseWeatherProvider    │
  │   - Date-Partitioned Raw Lakehouse Storage   │
  └──────────────────────┬───────────────────────┘
                         ▼
  ┌──────────────────────────────────────────────┐
  │     2. Validation & Spatio-Temporal Sync     │
  │   - Physical Bounds Check ([0, 1500] µg/m³)  │
  │   - Stuck Sensor / Flatline Telemetry Filter │
  │   - Hourly Regularization & Bounded Ffill    │
  │   - Spatial Alignment (Haversine & IDW)      │
  │   - CPCB IND-AQI Sub-Index Calculation       │
  └──────────────────────┬───────────────────────┘
                         ▼
  ┌──────────────────────────────────────────────┐
  │    3. Atmospheric Feature Engineering        │
  │   - Zonal (u) & Meridional (v) Wind Vectors  │
  │   - Atmospheric Ventilation Index (VI)       │
  │   - Nocturnal Inversion & Cooling Proxy      │
  │   - Hygroscopic Aerosol Growth (>70% RH)     │
  │   - Diurnal/Seasonal Periodic Transformations│
  │   - Autoregressive Lags & Rolling Statistics │
  └──────────────────────┬───────────────────────┘
                         ▼
  ┌──────────────────────────────────────────────┐
  │    4. Multi-Horizon Coupled Modeling         │
  │   - Persistence & Seasonal Diurnal Baselines │
  │   - Weather-Coupled LightGBM (L1 Robust MAE) │
  │   - Chronological Expanding Window Validation│
  │   - Model Registry & Champion Pointer        │
  └──────────────────────┬───────────────────────┘
                         ▼
  ┌──────────────────────────────────────────────┐
  │           5. Serving & Productization        │
  │   - Scheduled Ingestion & Inference Worker   │
  │   - FastAPI REST API (Port 8000)             │
  │   - Streamlit Geospatial Dashboard (Port 8501│
  │   - Docker Compose Multi-Container Stack     │
  └──────────────────────────────────────────────┘
```

---

## 🌬️ Atmospheric Physics & Coupled Features

Delhi's winter air quality crisis is heavily governed by local atmospheric dynamics. This system implements domain-specific physical terms:

1. **Wind Vector Decomposition ($u, v$)**:
   $$\text{Wind}_u = -\text{wind\_speed} \cdot \sin(\theta), \quad \text{Wind}_v = -\text{wind\_speed} \cdot \cos(\theta)$$
   Separates zonal (stubble-smoke transport from northwest) and meridional wind dispersion.
2. **Atmospheric Ventilation Index ($VI$)**:
   $$VI = \text{wind\_speed\_10m} \times \text{boundary\_layer\_height}$$
   When $VI < 2000\text{ m}^2/\text{s}$, horizontal and vertical dispersion ceases, trapping smoke in the Delhi basin.
3. **Nocturnal Thermal Inversion Proxy**:
   Rapid evening surface cooling ($\Delta T_{1h}, \Delta T_{3h}$) combined with boundary layer collapse ($\text{PBLH} < 250\text{m}$) causes severe particulate accumulation.
4. **Hygroscopic Particle Growth**:
   Particulate mass increases non-linearly under high relative humidity ($\text{RH} > 70\%$) as water vapor condenses onto aerosol cores.

---

## Evaluation status

The repository contains model registry metadata, but its provenance and evaluation dataset are not documented well enough to treat the stored scores as a verified benchmark. No accuracy figures are presented here. Evaluation should be considered pending until the training run is reproduced against documented held-out observations.

---

## Quick Start

### Requirements

Install Docker Desktop (including Docker Compose v2), Git, Python 3.10+, and Node.js 18+. Node is checked for frontend tooling compatibility; the current dashboard is Streamlit. Live air-quality ingestion uses the OpenAQ v3 locations and per-location latest resources, and requires an API key. Create a key at [OpenAQ Explorer](https://explore.openaq.org/); the current general limit is 60 requests/minute and 2,000/hour per key, so the worker polls every 15 minutes and request volume scales with matched stations ([API key](https://docs.openaq.org/using-the-api/api-key), [rate limits](https://docs.openaq.org/using-the-api/rate-limits), [latest measurements](https://docs.openaq.org/resources/latest)). Weather uses Open-Meteo's public API without a key for non-commercial use; consult its [API documentation](https://open-meteo.com/en/docs) and [usage limits](https://open-meteo.com/en/pricing).

```bash
git clone https://github.com/ayushk-byte/delhi-aqi-weather-forecasting.git
cd delhi-aqi-weather-forecasting
cp .env.example .env
# Set OPENAQ_API_KEY in .env
./scripts/setup.sh
./scripts/dev.sh
```

On Windows PowerShell, run `Copy-Item .env.example .env`, edit `.env`, then run `.\scripts\setup.ps1` followed by `.\scripts\dev.ps1`.

Setup checks dependencies, creates a Python virtual environment, starts PostgreSQL and Redis, installs packages, runs the versioned SQL migration and structural station seed, probes both live providers, ingests actual observations, and verifies rows in PostgreSQL. Raw API payloads are also retained in date-partitioned JSON under `data/raw`. It fails on missing credentials or failed/empty live ingestion and never switches to mock data. Redis is checked with PING and PostgreSQL with schema queries.

Visit `http://localhost:8000/docs` (API), `http://localhost:8501` (dashboard), and `http://localhost:8000/api/system/health`. Run `./scripts/health-check.sh` (Windows: `.\scripts\health-check.ps1`) to check backend, PostgreSQL, Redis, and live provider availability. Stop with `./scripts/stop.sh` / `.\scripts\stop.ps1`. To delete local database and observation data, run `./scripts/reset.sh` / `.\scripts\reset.ps1` and type `DELETE` when prompted.

The first live ingestion establishes current AQI/weather readings but does not create a long training history. Forecast and training APIs deliberately remain unavailable until sufficient aligned observations with verified non-mock provider provenance exist and a model artifact is loadable; no prediction is fabricated to make the initial dashboard look populated.

## 🚀 Local Development (manual)

### Option 1: Local Virtual Environment

```bash
# 1. Clone the repository
git clone https://github.com/ayushk-byte/delhi-aqi-weather-forecasting.git
cd delhi-aqi-weather-forecasting

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
.\.venv\Scripts\Activate.ps1    # On Windows PowerShell

# 3. Install dependencies
pip install -r requirements-dev.txt
pip install -e . --no-deps

# 4. Copy configuration
cp .env.example .env
```

#### Run Pipelines:

```bash
# Ingest live provider observations (configure OPENAQ_API_KEY in .env)
python -m src.pipelines.ingest_pipeline --aqi-provider openaq --weather-provider open_meteo

# Train and benchmark only when verified real aligned observations exist
python -m src.pipelines.training_pipeline --pollutant pm25

# Generate real-time forecasts
python -m src.pipelines.inference_pipeline

# Start background scheduler worker
python -m src.pipelines.worker --interval-minutes 60
```

#### Launch Services:

```bash
# Start FastAPI REST API (http://localhost:8000/docs)
uvicorn src.api.main:app --reload --port 8000

# Start Streamlit Dashboard (http://localhost:8501)
streamlit run ui/app.py
```

---

### Option 2: Docker Compose

Spin up the entire stack (FastAPI, Streamlit Dashboard, and Background Worker) with a single command:

```bash
cd docker
docker compose up --build -d
```

- **REST API & Swagger Docs**: `http://localhost:8000/docs`
- **Interactive Dashboard**: `http://localhost:8501`

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service liveness, environment, and registered champion models |
| `GET` | `/forecast/latest` | Latest regional city-wide and station-by-station multi-horizon forecast |
| `GET` | `/forecast/station/{id}` | Targeted forecast for a specific station (e.g. `/forecast/station/DL001`) |
| `POST`| `/forecast/run` | On-demand execution of real-time inference pipeline |
| `GET` | `/observations/stations`| Directory of reference monitoring stations with coordinates |
| `GET` | `/observations/current` | Most recent recorded observations and weather variables |

#### Health Query:
```bash
curl http://localhost:8000/api/system/health
```

---

## 🧪 Testing & Code Quality

The repository includes a comprehensive automated test suite (unit tests and end-to-end integration tests):

```bash
# Run complete test suite
pytest -v

# Run with test coverage
pytest -v --cov=src --cov-report=term-missing

# Lint and check formatting with Ruff
ruff check src tests ui
ruff format --check src tests ui
```

---

## 🗺️ Monitored Stations

| ID | Station Name | Zone | Latitude | Longitude | CPCB Code |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **DL001** | Anand Vihar, Delhi - DPCC | East Delhi | 28.6473 | 77.3158 | site_115 |
| **DL002** | Punjabi Bagh, Delhi - DPCC | West Delhi | 28.6740 | 77.1310 | site_118 |
| **DL003** | R K Puram, Delhi - DPCC | South Delhi | 28.5632 | 77.1869 | site_119 |
| **DL004** | ITO, Delhi - CPCB | Central Delhi | 28.6286 | 77.2410 | site_103 |
| **DL005** | Dwarka-Sector 8, Delhi - DPCC | South West Delhi | 28.5710 | 77.0667 | site_122 |
| **DL006** | Jahangirpuri, Delhi - DPCC | North Delhi | 28.7328 | 77.1706 | site_114 |
| **DL007** | Bawana, Delhi - DPCC | North West Delhi | 28.7762 | 77.0511 | site_113 |
| **DL008** | Wazirpur, Delhi - DPCC | North West Delhi | 28.6998 | 77.1654 | site_125 |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
