"""Modern 72-Hour Weather-Coupled Air Quality Forecaster Dashboard for Delhi NCR."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure root directory in python path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.core.constants import CPCB_AQI_CATEGORIES, DELHI_STATIONS
from ui.api_client import DashboardAPIClient

# Page configuration
st.set_page_config(
    page_title="VayuVani AI — Delhi NCR 72h Coupled AQI Forecaster",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for classy, premium dark glassmorphism aesthetic
st.markdown(
    """
    <style>
        /* Global page background and font smoothing */
        .stApp {
            background-color: #080c14;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2.5rem;
            max-width: 96%;
        }

        /* Hero Command Center Header */
        .hero-banner {
            background: radial-gradient(circle at 15% 30%, #1e293b 0%, #0f172a 80%);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 18px;
            padding: 24px 32px;
            margin-bottom: 18px;
            box-shadow: 0 16px 36px -10px rgba(0, 0, 0, 0.55);
            position: relative;
            overflow: hidden;
        }
        .brand-header {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .logo-box {
            width: 58px;
            height: 58px;
            background: linear-gradient(135deg, rgba(14, 165, 233, 0.18) 0%, rgba(16, 185, 129, 0.18) 100%);
            border: 1.5px solid rgba(56, 189, 248, 0.45);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 25px rgba(56, 189, 248, 0.25);
            flex-shrink: 0;
        }
        .hero-edition {
            background: rgba(56, 189, 248, 0.1);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 6px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.8px;
        }
        .hero-tag-row {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 10px;
        }
        .hero-chip {
            background: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 9999px;
            padding: 3px 12px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }
        .live-dot {
            height: 8px;
            width: 8px;
            background-color: #10b981;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 10px #10b981;
        }
        .hero-title {
            font-size: 32px;
            font-weight: 800;
            color: #ffffff;
            margin: 0;
            letter-spacing: -0.8px;
            line-height: 1.2;
        }
        .hero-subtitle {
            font-size: 14.5px;
            color: #94a3b8;
            margin-top: 8px;
            margin-bottom: 0;
            line-height: 1.5;
        }

        /* Control Strip Bar */
        .control-bar {
            background: #111827;
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 14px;
            padding: 14px 22px;
            margin-bottom: 22px;
            display: flex;
            align-items: center;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
        }

        /* 72-Hour Outlook Cards */
        .card-stat {
            border-radius: 14px;
            padding: 20px 22px;
            margin-bottom: 12px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: all 0.2s ease-in-out;
            min-height: 165px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .card-stat:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.45);
        }
        .card-label {
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .card-val {
            font-size: 36px;
            font-weight: 800;
            margin: 6px 0;
            line-height: 1;
        }
        .card-sub {
            font-size: 13.5px;
            font-weight: 600;
            color: #e2e8f0;
        }
        .badge-pill {
            display: inline-block;
            padding: 4px 11px;
            border-radius: 9999px;
            font-size: 11.5px;
            font-weight: 700;
            margin-top: 6px;
        }

        /* Feedback diagnostics boxes */
        .feedback-box {
            background-color: #111827;
            border-left: 4px solid #38bdf8;
            border-radius: 12px;
            padding: 18px 22px;
            margin-top: 14px;
            margin-bottom: 14px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
        }

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.15);
            padding-bottom: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 13.5px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# CPCB Color Mapping
CPCB_COLOR_MAP = {
    "Good": "#009966",
    "Satisfactory": "#7CB342",
    "Moderate": "#F59E0B",
    "Poor": "#EF4444",
    "Very Poor": "#8B5CF6",
    "Severe": "#881337",
}

client = DashboardAPIClient()


@st.cache_data(ttl=120)
def load_forecast_bundle():
    return client.get_latest_forecast()


bundle = load_forecast_bundle()
if bundle.get("status") != "success":
    st.error(f"❌ {bundle.get('reason', 'Could not load live forecast bundle.')}")
    st.stop()

stations_list = bundle.get("stations", [])
if not stations_list:
    st.warning("No station forecast data available.")
    st.stop()

station_dict = {s["station_name"]: s for s in stations_list}

# ==================== CLASSY HERO BANNER ====================
st.markdown(
    f"""
    <div class="hero-banner">
        <div class="hero-tag-row">
            <span class="hero-chip"><span class="live-dot"></span> LIVE COUPLED STREAM</span>
            <span class="hero-chip">72-HOUR OUTLOOK</span>
            <span class="hero-chip">CPCB STANDARDS</span>
            <span style="font-size: 12px; color: #94a3b8; margin-left: auto;">
                Synced: <b>{bundle.get('last_updated', 'Current Hour')}</b>
            </span>
        </div>
        <div class="brand-header">
            <div class="logo-box">
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 12C4 9.79086 5.79086 8 8 8H17C18.6569 8 20 9.34315 20 11C20 12.6569 18.6569 14 17 14H15" stroke="url(#paint0_linear)" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M2 16C2 14.3431 3.34315 13 5 13H13C14.6569 13 16 14.3431 16 16C16 17.6569 14.6569 19 13 19H7" stroke="url(#paint1_linear)" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M6 7C6 5.34315 7.34315 4 9 4H14C15.6569 4 17 5.34315 17 7" stroke="#38bdf8" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>
                    <circle cx="19" cy="7" r="1.8" fill="#10b981"/>
                    <defs>
                        <linearGradient id="paint0_linear" x1="4" y1="8" x2="20" y2="14" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#38bdf8"/>
                            <stop offset="1" stop-color="#818cf8"/>
                        </linearGradient>
                        <linearGradient id="paint1_linear" x1="2" y1="13" x2="16" y2="19" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#10b981"/>
                            <stop offset="1" stop-color="#38bdf8"/>
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            <div>
                <div style="display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;">
                    <h1 class="hero-title">VayuVani <span style="color: #38bdf8; font-weight: 300;">AI</span></h1>
                    <span class="hero-edition">DELHI NCR 72H COUPLED FORECASTER</span>
                </div>
                <p class="hero-subtitle">
                    Dynamic Two-Way Feedback • Atmospheric Inversion Capping • Regional Stubble Plume Detection • CPCB IND-AQI
                </p>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==================== CONTROL STRIP BAR ====================
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1.8, 1.4, 0.8])

with col_ctrl1:
    selected_name = st.selectbox(
        "📍 Monitoring Station",
        options=list(station_dict.keys()),
        index=0,
        label_visibility="collapsed",
    )

active_stn = station_dict[selected_name]
current = active_stn["current"]
snapshots = active_stn["horizon_snapshots"]
trajectory = active_stn["trajectory_72h"]

with col_ctrl2:
    st.markdown(
        f"""
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 7px 14px; font-size: 12.5px; color: #cbd5e1; display: flex; align-items: center; justify-content: space-between;">
            <span>Zone: <b>{active_stn.get('zone', 'Delhi NCR')}</b></span>
            <span>Coord: <b>{active_stn.get('latitude', 0):.3f}N, {active_stn.get('longitude', 0):.3f}E</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_ctrl3:
    if st.button("🔄 Sync Live", use_container_width=True):
        with st.spinner("Syncing live feeds in parallel..."):
            client.get_latest_forecast(force_refresh=True)
            st.cache_data.clear()
        st.rerun()

st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

# ==================== 72-HOUR OUTLOOK KPI CARDS ====================
c_now, c_24, c_48, c_72 = st.columns(4)

# Current Card
curr_cat = current.get("aqi_category", "Moderate")
curr_color = CPCB_COLOR_MAP.get(curr_cat, "#F59E0B")
with c_now:
    st.markdown(
        f"""
        <div class="card-stat" style="background: linear-gradient(145deg, {curr_color}18 0%, #111827 75%); border-left: 5px solid {curr_color};">
            <div>
                <div class="card-label" style="color: {curr_color};">● CURRENT OBSERVED</div>
                <div class="card-val" style="color: {curr_color};">{current.get('cpcb_aqi')} <span style="font-size: 15px; color: #94a3b8; font-weight: 500;">AQI</span></div>
                <div class="card-sub">{curr_cat} • Dominant: <span style="color: {curr_color};">{current.get('dominant_pollutant', 'PM2.5').upper()}</span></div>
            </div>
            <div class="badge-pill" style="background-color: {curr_color}25; color: {curr_color};">
                PM2.5: {current.get('pm25')} µg/m³ • O3: {current.get('ozone')} µg/m³
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# +24h Card
snap_24 = next((s for s in snapshots if s["horizon_hours"] == 24), snapshots[0])
cat_24 = snap_24["aqi_category"]
color_24 = CPCB_COLOR_MAP.get(cat_24, "#F59E0B")
with c_24:
    st.markdown(
        f"""
        <div class="card-stat" style="background: linear-gradient(145deg, {color_24}18 0%, #111827 75%); border-left: 5px solid {color_24};">
            <div>
                <div class="card-label" style="color: {color_24};">TOMORROW (+24H)</div>
                <div class="card-val" style="color: {color_24};">{snap_24['predicted_aqi']} <span style="font-size: 15px; color: #94a3b8; font-weight: 500;">AQI</span></div>
                <div class="card-sub">{cat_24} • {snap_24['inversion_category']}</div>
            </div>
            <div class="badge-pill" style="background-color: {color_24}25; color: {color_24};">
                PBLH: {round(snap_24['pbl_height_m'])}m • Wind: {snap_24['wind_speed_ms']} m/s
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# +48h Card
snap_48 = next((s for s in snapshots if s["horizon_hours"] == 48), snapshots[1])
cat_48 = snap_48["aqi_category"]
color_48 = CPCB_COLOR_MAP.get(cat_48, "#F59E0B")
with c_48:
    st.markdown(
        f"""
        <div class="card-stat" style="background: linear-gradient(145deg, {color_48}18 0%, #111827 75%); border-left: 5px solid {color_48};">
            <div>
                <div class="card-label" style="color: {color_48};">DAY 2 (+48H)</div>
                <div class="card-val" style="color: {color_48};">{snap_48['predicted_aqi']} <span style="font-size: 15px; color: #94a3b8; font-weight: 500;">AQI</span></div>
                <div class="card-sub">{cat_48} • Inversion: <b>{round(snap_48['inversion_index'])}%</b></div>
            </div>
            <div class="badge-pill" style="background-color: {color_48}25; color: {color_48};">
                Confidence Band: [{snap_48['lower_bound']} - {snap_48['upper_bound']}]
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# +72h Card
snap_72 = next((s for s in snapshots if s["horizon_hours"] == 72), snapshots[-1])
cat_72 = snap_72["aqi_category"]
color_72 = CPCB_COLOR_MAP.get(cat_72, "#F59E0B")
with c_72:
    st.markdown(
        f"""
        <div class="card-stat" style="background: linear-gradient(145deg, {color_72}18 0%, #111827 75%); border-left: 5px solid {color_72};">
            <div>
                <div class="card-label" style="color: {color_72};">DAY 3 (+72H OUTLOOK)</div>
                <div class="card-val" style="color: {color_72};">{snap_72['predicted_aqi']} <span style="font-size: 15px; color: #94a3b8; font-weight: 500;">AQI</span></div>
                <div class="card-sub">{cat_72} • Stubble Risk: <b>{round(snap_72['stubble_plume_index'])}%</b></div>
            </div>
            <div class="badge-pill" style="background-color: {color_72}25; color: {color_72};">
                Confidence Band: [{snap_72['lower_bound']} - {snap_72['upper_bound']}]
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# ==================== MAIN DASHBOARD TABS ====================
tab_charts, tab_map, tab_feedback, tab_xai, tab_table = st.tabs([
    "📈 72h Coupled Trajectory",
    "🗺️ Delhi NCR Spatial Hotspots",
    "🔬 Atmospheric Inversion & Two-Way Feedback",
    "💡 Explainable AI & Health Alerts",
    "📋 All Stations 72h Table",
])

# ----------------- TAB 1: 72H COUPLED TRAJECTORY -----------------
with tab_charts:
    st.subheader(f"72-Hour Continuous Coupled Forecast Trajectory — {active_stn['station_name']}")
    st.caption("Demonstrating the physical coupling: Falling Boundary Layer Height (PBLH) & calm winds directly trigger AQI/PM2.5 accumulation.")

    df_traj = pd.DataFrame(trajectory)
    if "hour_label" not in df_traj.columns and "step_hour" in df_traj.columns:
        df_traj["hour_label"] = df_traj["step_hour"].apply(lambda h: f"+{h}h")

    # Dual Axis Subplots with NO OVERWRITING: Legend placed cleanly below the entire chart
    fig_coupled = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=(
            "Chemical Concentration Forecast (AQI, PM2.5 & Ozone O3)",
            "Atmospheric Physics Dynamics (Planetary Boundary Layer Height & Wind Speed)",
        ),
        row_heights=[0.58, 0.42],
    )

    # Upper Subplot: AQI & Pollutants
    # 90% Confidence envelope
    fig_coupled.add_trace(
        go.Scatter(
            x=df_traj["hour_label"],
            y=df_traj["aqi_upper_bound"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        ),
        row=1,
        col=1,
    )
    fig_coupled.add_trace(
        go.Scatter(
            x=df_traj["hour_label"],
            y=df_traj["aqi_lower_bound"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(56, 189, 248, 0.12)",
            line=dict(width=0),
            name="90% Confidence Interval",
        ),
        row=1,
        col=1,
    )

    # AQI Line
    fig_coupled.add_trace(
        go.Scatter(
            x=df_traj["hour_label"],
            y=df_traj["aqi"],
            mode="lines+markers",
            name="AQI Forecast",
            line=dict(color="#38bdf8", width=3),
            marker=dict(size=4),
        ),
        row=1,
        col=1,
    )

    # PM2.5 Line
    fig_coupled.add_trace(
        go.Scatter(
            x=df_traj["hour_label"],
            y=df_traj["pm25"],
            mode="lines",
            name="PM2.5 (µg/m³)",
            line=dict(color="#f43f5e", width=2, dash="dot"),
        ),
        row=1,
        col=1,
    )

    # Ground-level Ozone Line
    fig_coupled.add_trace(
        go.Scatter(
            x=df_traj["hour_label"],
            y=df_traj["ozone"],
            mode="lines",
            name="Ozone O3 (µg/m³)",
            line=dict(color="#a855f7", width=2, dash="dash"),
        ),
        row=1,
        col=1,
    )

    # CPCB Guideline Horizontal Thresholds
    fig_coupled.add_hline(y=100, line_dash="dash", line_color="#F59E0B", annotation_text="Moderate (100)", row=1, col=1)
    fig_coupled.add_hline(y=200, line_dash="dash", line_color="#EF4444", annotation_text="Poor (200)", row=1, col=1)
    fig_coupled.add_hline(y=300, line_dash="dash", line_color="#8B5CF6", annotation_text="Very Poor (300)", row=1, col=1)
    fig_coupled.add_hline(y=400, line_dash="dash", line_color="#881337", annotation_text="Severe (400)", row=1, col=1)

    # Lower Subplot: Atmospheric Boundary Layer & Wind Speed
    fig_coupled.add_trace(
        go.Scatter(
            x=df_traj["hour_label"],
            y=df_traj["pbl_height_m"],
            mode="lines",
            name="PBL Height (meters)",
            fill="tozeroy",
            fillcolor="rgba(16, 185, 129, 0.15)",
            line=dict(color="#10b981", width=2),
        ),
        row=2,
        col=1,
    )

    fig_coupled.add_trace(
        go.Scatter(
            x=df_traj["hour_label"],
            y=df_traj["wind_speed_ms"] * 100,
            mode="lines",
            name="Wind Speed (m/s x100)",
            line=dict(color="#fbbf24", width=2, dash="dashdot"),
        ),
        row=2,
        col=1,
    )

    # Clean layout with legend placed neatly at the bottom with no collision
    fig_coupled.update_layout(
        height=660,
        margin=dict(l=25, r=25, t=50, b=70),
        legend=dict(orientation="h", y=-0.14, x=0.5, xanchor="center", font=dict(size=12)),
        hovermode="x unified",
        template="plotly_dark",
    )
    st.plotly_chart(fig_coupled, use_container_width=True)

# ----------------- TAB 2: SPATIAL HOTSPOT MAP -----------------
with tab_map:
    st.subheader("Delhi NCR Spatial Pollution & Hotspot Map (+24h Outlook)")
    st.caption("Visualizing spatial heterogeneity across monitoring stations: hotspot zones show where atmospheric trapping is concentrated.")

    selected_map_h = st.radio("Select Forecast Horizon for Map:", [6, 12, 24, 48, 72], index=2, horizontal=True)

    map_rows = []
    for stn in stations_list:
        snap = next((s for s in stn["horizon_snapshots"] if s["horizon_hours"] == selected_map_h), stn["horizon_snapshots"][0])
        map_rows.append({
            "Station": stn["station_name"],
            "Zone": stn["zone"],
            "lat": stn["latitude"],
            "lon": stn["longitude"],
            "Predicted AQI": snap["predicted_aqi"],
            "Category": snap["aqi_category"],
            "PM2.5 (µg/m³)": snap["predicted_pm25"],
            "Ozone (µg/m³)": snap["predicted_o3"],
            "PBL Height (m)": round(snap["pbl_height_m"]),
            "Inversion": snap["inversion_category"],
            "Size": max(20, snap["predicted_aqi"] / 8.0),
        })

    map_df = pd.DataFrame(map_rows)

    scatter_fn = getattr(px, "scatter_map", getattr(px, "scatter_mapbox", None))
    style_param = (
        {"map_style": "carto-darkmatter"}
        if hasattr(px, "scatter_map")
        else {"mapbox_style": "carto-darkmatter"}
    )

    fig_map = scatter_fn(
        map_df,
        lat="lat",
        lon="lon",
        hover_name="Station",
        hover_data=["Predicted AQI", "Category", "PM2.5 (µg/m³)", "Ozone (µg/m³)", "PBL Height (m)", "Inversion"],
        color="Category",
        color_discrete_map=CPCB_COLOR_MAP,
        size="Size",
        zoom=10.2,
        center={"lat": 28.66, "lon": 77.19},
        height=540,
        **style_param,
    )
    fig_map.update_layout(
        margin=dict(r=0, t=0, l=0, b=0),
        legend=dict(orientation="h", y=0.02, x=0.02, bgcolor="rgba(15, 23, 42, 0.8)"),
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # Hotspot summary cards
    sorted_hotspots = map_df.sort_values("Predicted AQI", ascending=False)
    st.markdown("#### 🔥 Critical Hotspot Ranking (+24h)")
    h_cols = st.columns(min(4, len(sorted_hotspots)))
    for idx, (_, r) in enumerate(sorted_hotspots.head(4).iterrows()):
        with h_cols[idx]:
            cat_col = CPCB_COLOR_MAP.get(r["Category"], "#F59E0B")
            st.markdown(
                f"""
                <div style="background-color: #111827; border-left: 4px solid {cat_col}; padding: 14px 16px; border-radius: 10px;">
                    <div style="font-size: 11px; font-weight: 700; color: #94a3b8;">#{idx+1} {r['Zone'].upper()}</div>
                    <div style="font-size: 15px; font-weight: 700; margin: 4px 0; color: #f8fafc;">{r['Station'].split(',')[0]}</div>
                    <div style="font-size: 18px; font-weight: 800; color: {cat_col};">{r['Predicted AQI']} AQI • {r['Category']}</div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">PBL: {r['PBL Height (m)']}m • PM2.5: {r['PM2.5 (µg/m³)']}&micro;g</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ----------------- TAB 3: COUPLED FEEDBACK & INVERSION -----------------
with tab_feedback:
    st.subheader("🔬 Two-Way Meteorology-Chemistry Feedback & Inversion Tracking")
    st.caption("Detailed diagnostics of atmospheric thermal inversion, aerosol-radiation feedback, and regional stubble burning advection.")

    f_col1, f_col2, f_col3 = st.columns(3)

    inv = current.get("inversion", {})
    plume = current.get("stubble_plume", {})
    rad_feed = current.get("aerosol_feedback", {})

    with f_col1:
        st.markdown(
            f"""
            <div class="feedback-box" style="border-left-color: #ef4444;">
                <h4 style="margin: 0; color: #ef4444;">🌡️ Atmospheric Inversion Capping</h4>
                <div style="font-size: 28px; font-weight: 800; margin: 8px 0;">{inv.get('inversion_index', 0)}% <span style="font-size: 14px; color: #94a3b8;">Index</span></div>
                <p style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">Status: {inv.get('category')}</p>
                <p style="font-size: 12px; color: #94a3b8; line-height: 1.4;">{inv.get('description')}</p>
                <div style="font-size: 12px; color: #cbd5e1; margin-top: 8px;">
                    • Planetary Boundary Layer: <b>{round(inv.get('pbl_height_m', 0))} m</b><br>
                    • Surface Wind Speed: <b>{inv.get('wind_speed_ms', 0)} m/s</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with f_col2:
        st.markdown(
            f"""
            <div class="feedback-box" style="border-left-color: #f97316;">
                <h4 style="margin: 0; color: #f97316;">🚜 Regional Stubble Plume Corridor</h4>
                <div style="font-size: 28px; font-weight: 800; margin: 8px 0;">{plume.get('plume_index', 0)}% <span style="font-size: 14px; color: #94a3b8;">Influx</span></div>
                <p style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">Risk Level: {plume.get('status')}</p>
                <p style="font-size: 12px; color: #94a3b8; line-height: 1.4;">{plume.get('summary')}</p>
                <div style="font-size: 12px; color: #cbd5e1; margin-top: 8px;">
                    • Transport Wind Angle: <b>{plume.get('wind_direction_deg', 0)}° (NW Corridor)</b><br>
                    • Transport Velocity: <b>{plume.get('wind_speed_ms', 0)} m/s</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with f_col3:
        st.markdown(
            f"""
            <div class="feedback-box" style="border-left-color: #38bdf8;">
                <h4 style="margin: 0; color: #38bdf8;">☀️ Aerosol-Radiation Feedback</h4>
                <div style="font-size: 28px; font-weight: 800; margin: 8px 0;">-{rad_feed.get('temperature_depression_deg_c', 0)}°C <span style="font-size: 14px; color: #94a3b8;">Cooling</span></div>
                <p style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">PBL Suppression: -{rad_feed.get('pbl_suppression_pct', 0)}%</p>
                <p style="font-size: 12px; color: #94a3b8; line-height: 1.4;">
                    Solar dimming from dense aerosol concentrations attenuates ground heating, cooling surface temperatures and compressing boundary layer height from {rad_feed.get('base_pbl_height_m')}m down to {rad_feed.get('effective_pbl_height_m')}m.
                </p>
                <div style="font-size: 12px; color: #cbd5e1; margin-top: 8px;">
                    • Feedback Trapping Amplification: <b>+{round(rad_feed.get('feedback_amplified_pm25', 0) - current.get('pm25', 0), 1)} µg/m³ PM2.5</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 72-Hour Inversion & Stubble Timeline
    st.markdown("#### 🕒 72-Hour Inversion Strength & Regional Plume Timeline")
    df_timeline = pd.DataFrame(trajectory)
    if "hour_label" not in df_timeline.columns and "step_hour" in df_timeline.columns:
        df_timeline["hour_label"] = df_timeline["step_hour"].apply(lambda h: f"+{h}h")
    fig_time = go.Figure()
    fig_time.add_trace(go.Scatter(
        x=df_timeline["hour_label"],
        y=df_timeline["inversion_index"],
        mode="lines+markers",
        name="Atmospheric Inversion Strength Index (%)",
        line=dict(color="#ef4444", width=3),
    ))
    fig_time.add_trace(go.Scatter(
        x=df_timeline["hour_label"],
        y=df_timeline["stubble_plume_index"],
        mode="lines",
        name="NW Stubble Plume Influx Index (%)",
        line=dict(color="#f97316", width=2, dash="dash"),
    ))
    fig_time.add_hline(y=70, line_dash="dot", line_color="#dc2626", annotation_text="Severe Inversion Trap (>70%)")
    fig_time.update_layout(
        height=340,
        margin=dict(l=25, r=25, t=40, b=60),
        legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center"),
        hovermode="x unified",
        template="plotly_dark",
    )
    st.plotly_chart(fig_time, use_container_width=True)

# ----------------- TAB 4: EXPLAINABLE AI & HEALTH ALERTS -----------------
with tab_xai:
    x_col1, x_col2 = st.columns([1.2, 1])

    with x_col1:
        st.subheader("💡 Explainable AI (XAI): Why Is AQI Changing?")
        st.caption("Model-derived feature attribution: Isolating the physical-chemical drivers behind future predictions.")

        horizon_choice = st.selectbox("Select Forecast Horizon to Explain:", [24, 48, 72], index=0)
        xai_data = DashboardAPIClient.get_explainability(active_stn, horizon_choice)

        st.info(f"**Diagnostic Summary (+{horizon_choice}h)**: {xai_data['explanation']}")

        factors_df = pd.DataFrame(xai_data["factors"])
        fig_bar = px.bar(
            factors_df,
            x="percentage",
            y="name",
            orientation="h",
            text="percentage",
            color="name",
            color_discrete_map={f["name"]: f["color"] for f in xai_data["factors"]},
            labels={"percentage": "Attribution Impact (%)", "name": "Driver"},
            height=280,
        )
        fig_bar.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_bar.update_layout(
            showlegend=False,
            margin=dict(l=10, r=30, t=20, b=20),
            template="plotly_dark",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with x_col2:
        st.subheader("📢 Forecast-Based Alerts & Public Health Advisory")
        st.caption("Actionable recommendations based on official CPCB India Air Quality guidelines.")

        alerts = DashboardAPIClient.get_forecast_alerts(active_stn)
        for al in alerts:
            st.markdown(
                f"""
                <div style="background-color: #111827; border-left: 5px solid {al['color']}; padding: 16px 18px; border-radius: 10px; margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 800; color: {al['color']};">{al['badge']}</span>
                    </div>
                    <h4 style="margin: 6px 0; color: #f8fafc;">{al['title']}</h4>
                    <p style="font-size: 13px; color: #cbd5e1; margin-bottom: 10px;">{al['message']}</p>
                    <div style="background-color: rgba(0, 0, 0, 0.25); padding: 10px 12px; border-radius: 6px;">
                        <div style="font-size: 11px; font-weight: 700; color: #94a3b8; margin-bottom: 4px;">RECOMMENDED ACTIONS:</div>
                        <ul style="margin: 0; padding-left: 18px; font-size: 12px; color: #e2e8f0; line-height: 1.5;">
                            {''.join(f'<li>{adv}</li>' for adv in al['advisories'])}
                        </ul>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ----------------- TAB 5: ALL STATIONS BREAKDOWN -----------------
with tab_table:
    st.subheader("📋 Delhi NCR Regional Stations Multi-Horizon Overview")
    st.caption("Complete tabular comparison of all monitoring stations across 24h, 48h, and 72h forecast horizons.")

    table_data = []
    for stn in stations_list:
        curr_s = stn["current"]
        s24 = next((s for s in stn["horizon_snapshots"] if s["horizon_hours"] == 24), {})
        s48 = next((s for s in stn["horizon_snapshots"] if s["horizon_hours"] == 48), {})
        s72 = next((s for s in stn["horizon_snapshots"] if s["horizon_hours"] == 72), {})

        table_data.append({
            "Station Name": stn["station_name"],
            "Zone": stn["zone"],
            "Current AQI": curr_s.get("cpcb_aqi"),
            "Current Category": curr_s.get("aqi_category"),
            "+24h AQI": s24.get("predicted_aqi"),
            "+24h Category": s24.get("aqi_category"),
            "+48h AQI": s48.get("predicted_aqi"),
            "+48h Category": s48.get("aqi_category"),
            "+72h AQI": s72.get("predicted_aqi"),
            "+72h Category": s72.get("aqi_category"),
            "Inversion Status": s24.get("inversion_category"),
        })

    table_df = pd.DataFrame(table_data)
    st.dataframe(table_df, use_container_width=True, hide_index=True)

# Clean, professional footer
st.markdown("---")
st.markdown(
    """
    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #64748b;">
        <span><b>VayuVani AI: Delhi NCR 72-Hour Weather-Coupled Air Quality Forecaster</b> (SIH Prototype)</span>
        <span>Model: <code>weather_coupled_wrf_chem_lightgbm_feedback_v2</code> • Live Open-Meteo & CPCB Standards</span>
    </div>
    """,
    unsafe_allow_html=True,
)
