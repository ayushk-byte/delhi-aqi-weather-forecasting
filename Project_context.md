# Project Context: Delhi NCR Air Pollution–Weather Coupled Forecasting System

## 1. Project Overview
- **One-line description**: An explainable, spatially aware AQI forecasting system for Delhi NCR that combines pollution and meteorological information to forecast future air quality and explain the factors driving predicted changes.
- **Problem being solved**: Conventional AQI forecasting approaches can treat pollution levels and meteorological/dispersion conditions too independently, limiting their ability to explain why AQI changes and where pollution hotspots may emerge.
- **Target geography/domain**: Delhi NCR / urban air-quality forecasting.
- **Core Pitch**: *"We don't just predict tomorrow's AQI—we show where pollution may rise and explain why."*

## 2. Core Innovations (The 5 System-Level Pillars)
1. **Joint Meteorology–Pollution Forecasting**: Integrates atmospheric dispersion physics, ventilation index, and NWP weather forecasts with historical pollution time series.
2. **Explainable AQI Forecasting**: Model-derived feature attribution answering: *"Why is this forecast changing?"* by categorizing contributions into Meteorological, Pollution, and Temporal drivers.
3. **Spatial AQI/Pollution Forecasting**: Represents pollution heterogeneity across individual Delhi NCR stations/locations rather than an opaque single city-wide number.
4. **Forecast-Based Hotspot Detection**: Compares spatial predictions across locations to proactively flag emerging pollution hotspots before they peak.
5. **Forecast + Explanation + Alert in One Interface**: Unified workflow combining:
   `Current State -> Multi-Horizon Forecast -> Spatial Hotspots -> XAI Explanation -> Confidence/Uncertainty -> Decision-Support Alerts`.

## 3. Supported Horizons
- **+24 Hours**, **+48 Hours**, **+72 Hours** (and near-term **+6h, +12h**).

## 4. Operational Boundaries
- Avoid building complex WRF-Chem simulation models from scratch.
- Lightweight, explainable ML models (GBDT / LightGBM) with physical dispersion feature engineering.
