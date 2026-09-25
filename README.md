# 🌬️ VayuVani AI: Delhi NCR 72-Hour Weather-Coupled Air Quality Forecaster

[![CI Pipeline](https://github.com/ayushk-byte/delhi-aqi-weather-forecasting/actions/workflows/ci.yml/badge.svg)](https://github.com/ayushk-byte/delhi-aqi-weather-forecasting/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Smart India Hackathon](https://img.shields.io/badge/SIH-Ready%20Prototype-orange.svg)](#)

A high-resolution, physics-guided air quality forecasting platform designed specifically for the complex micro-climate and severe pollution episodes of the **Delhi National Capital Region (NCR)**.

Traditional models treat meteorology and pollution dispersion independently. **VayuVani AI** models the two-way atmospheric-chemical feedback loops:
1. **Atmospheric Inversion Dynamics**: Trapping particulate mass when planetary boundary layers (PBLH) collapse beneath nocturnal thermal caps.
2. **Aerosol-Radiation Feedback**: Particulate matter blocking incident solar radiation, lowering daytime surface temperatures and reinforcing boundary layer suppression.
3. **Regional Stubble-Burning Transport**: Quantifying north-westerly plume advection from Punjab/Haryana agricultural burning directly into the Delhi basin.

The engine delivers real-time forecasts across a continuous **72-hour horizon** with station-specific resolution and full explainability.

---

## 🏛️ System Architecture

```text
       [ Live CPCB / CAAQMS Feeds ]           [ Live Open-Meteo High-Res NWP ]
      (8 Strategic Delhi NCR Stations)      (Hourly Temp, Wind, RH, Boundary Layer)
                     │                                         │
                     └────────────────────┬────────────────────┘
                                          ▼
                         ┌─────────────────────────────────┐
                         │   1. Ultra-Fast Batch Ingest    │
                         │   Multi-coordinate concurrent   │
                         │   queries: 8 stations in ~2.4s  │
                         └────────────────┬────────────────┘
                                          ▼
                         ┌─────────────────────────────────┐
                         │ 2. Coupled Physics Engine       │
                         │ • Inversion Strength Index (ISI)│
                         │ • Stubble Plume Advection Index │
                         │ • Aerosol-Solar Dimming Effect  │
                         │ • Hygroscopic Particle Growth   │
                         └────────────────┬────────────────┘
                                          ▼
                         ┌─────────────────────────────────┐
                         │ 3. Multi-Horizon Forecasting    │
                         │ • Weather-Coupled GBDT Engine   │
                         │ • +6h, +12h, +24h, +48h, +72h   │
                         │ • Full 72-Hour Trajectory       │
                         └────────────────┬────────────────┘
                                          ▼
                         ┌─────────────────────────────────┐
                         │ 4. VayuVani AI Visual Command   │
                         │ • Spatial Hotspot Heatmaps      │
                         │ • Timeline & Diurnal Curves     │
                         │ • CPCB Graded Health Advisory   │
                         │ • Feature Attribution (SHAP/XAI)│
                         └─────────────────────────────────┘
```

---

## 🌬️ Atmospheric Physics & Coupled Features

Delhi's winter air pollution crisis is governed by complex land-atmosphere dynamics. VayuVani AI implements real-time domain-specific physical equations:

1. **Inversion Strength Index (ISI)**:
   $$ISI = \max\left(0, \frac{1500 - \text{PBLH}}{1500}\right) \times \left(1 + \max(0, \Delta T_{\text{cooling}})\right)$$
   Quantifies particulate trapping efficiency when nocturnal planetary boundary layers collapse under thermal caps.

2. **Regional Stubble-Burning Plume Transport Index**:
   Identifies atmospheric transport channels when north-westerly winds ($300^\circ - 330^\circ$) steer agricultural burning plumes from Punjab/Haryana into Delhi NCR.

3. **Atmospheric Ventilation Index ($VI$)**:
   $$VI = \text{wind\_speed\_10m} \times \text{boundary\_layer\_height}$$
   When $VI < 2000\text{ m}^2/\text{s}$, horizontal and vertical dispersion ceases, creating an emergency stagnation pocket.

4. **Aerosol-Radiation Feedback (Solar Dimming)**:
   Accounts for high aerosol optical depth (AOD) reflecting solar insolation, suppressing daytime boundary layer growth and trapping pollutants in a self-reinforcing loop.

5. **Hygroscopic Particle Growth**:
   Models exponential moisture absorption and secondary particulate formation when Relative Humidity ($\text{RH}$) exceeds $70\%$.

---

## 🗺️ Monitored Stations (CPCB / DPCC Reference Network)

| ID | Station Name | Zone | Latitude | Longitude | Critical Exposure Factor |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **DL001** | Anand Vihar, Delhi - DPCC | East Delhi | 28.6473 | 77.3158 | Heavy interstate bus transit & regional border inflow |
| **DL002** | Punjabi Bagh, Delhi - DPCC | West Delhi | 28.6740 | 77.1310 | Ring road arterial traffic & residential mix |
| **DL003** | R K Puram, Delhi - DPCC | South Delhi | 28.5632 | 77.1869 | Dense institutional & urban residential canopy |
| **DL004** | ITO, Delhi - CPCB | Central Delhi | 28.6286 | 77.2410 | High-density administrative corridor & transit junction |
| **DL005** | Dwarka-Sector 8, Delhi - DPCC | South West | 28.5710 | 77.0667 | Airport approach corridor & open southwest plains |
| **DL006** | Jahangirpuri, Delhi - DPCC | North Delhi | 28.7328 | 77.1706 | Direct northwest stubble plume entry gate |
| **DL007** | Bawana, Delhi - DPCC | North West | 28.7762 | 77.0511 | Major industrial cluster & northwest windward edge |
| **DL008** | Wazirpur, Delhi - DPCC | North West | 28.6998 | 77.1654 | Dense industrial manufacturing & smelting corridor |

---

## 🚀 Quick Start

### 1. Clone & Set Up Environment

```bash
# Clone the repository
git clone https://github.com/ayushk-byte/delhi-aqi-weather-forecasting.git
cd delhi-aqi-weather-forecasting

# Create Python virtual environment
python -m venv .venv

# Activate environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Install project dependencies
pip install -r requirements.txt
pip install -e . --no-deps
```

### 2. Launch VayuVani AI Dashboard

```bash
# Launch the interactive Streamlit command center
streamlit run ui/app.py --server.port 8502
```
Open **`http://localhost:8502`** in your browser to interact with:
- **Overview & 72-Hour Horizon Cards**: Live AQI readings, +6h, +12h, +24h, +48h, and +72h predictions with CPCB severity badges.
- **Geospatial Hotspots**: High-resolution interactive dark-matter cartographic maps with station markers sized and colored by AQI.
- **72-Hour Trajectory Analysis**: Hourly continuous forecasts alongside planetary boundary layer dynamics and wind vectors.
- **Atmospheric Physics Diagnostics**: Real-time Inversion Strength Index (ISI), Stubble-Burning Transport Index, and Ventilation Index gauges.
- **Explainable AI (XAI)**: Feature attribution breaking down the impact of meteorological, chemical, and temporal drivers.
- **CPCB Health Advisories**: Public safety and medical guidelines for vulnerable populations, schools, and outdoor activities.

### 3. Launch REST API (Optional)

```bash
uvicorn src.api.main:app --reload --port 8000
```
API Documentation & Swagger UI available at `http://localhost:8000/docs`.

---

## 🧪 Testing & Code Quality

```bash
# Run complete test suite
pytest -v

# Code quality check with Ruff
ruff check src tests ui
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
