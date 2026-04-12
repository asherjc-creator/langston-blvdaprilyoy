import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from datetime import datetime, timedelta
import os

# -----------------------------
# 1. Page Configuration & Styling
# -----------------------------
st.set_page_config(page_title="Econo Lodge Arlington Revenue Portal", layout="wide", page_icon="📈")

st.markdown("""
<style>
    .main { background-color:#f8f9fa; }
    .stMetric { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #eee; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    .event-card { padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 6px solid #ff4b4b; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 2. Robust Data Loading & Cleaning
# -----------------------------
def clean_numeric(val):
    if pd.isna(val): return 0.0
    val = str(val).replace(',', '').replace('$', '').replace('"', '').strip()
    if val in ['∞', '', 'nan', 'None']: return 0.0
    try:
        return float(val)
    except:
        return 0.0

@st.cache_data
def load_all_data():
    # Load Econo KPI Files
    kpi_files = {
        "2023": "ECONO - 2023.csv",
        "2024": "ECONO - 2024.csv",
        "2025": "ECONO - 2025.csv",
        "2026": "ECONO - 2026.csv"
    }
    
    df_list = []
    for year, path in kpi_files.items():
        if os.path.exists(path):
            temp = pd.read_csv(path)
            temp.rename(columns={'IDS_DATE': 'Date', 'RoomRev': 'Room_Revenue', 'Occupied': 'Rooms_Sold', 'Rooms': 'Total_Rooms'}, inplace=True)
            temp['Date'] = pd.to_datetime(temp['Date'], errors='coerce')
            temp = temp.dropna(subset=['Date'])
            for col in ['Room_Revenue', 'ADR', 'RevPAR', 'Rooms_Sold', 'Total_Rooms']:
                if col in temp.columns:
                    temp[col] = temp[col].apply(clean_numeric)
            temp['Year'] = int(year)
            df_list.append(temp)
    
    full_df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
    if not full_df.empty:
        full_df['Occupancy'] = np.where(full_df['Total_Rooms'] > 0, full_df['Rooms_Sold'] / full_df['Total_Rooms'], 0)
        # Lat/Lon for Econo Lodge Metro Arlington
        full_df['Lat'], full_df['Lon'] = 38.8856, -77.1664

    # Load Rate Code Files
    rc_files = {
        "2024": "Rate code 2024.xlsx - Rate code 2024.csv",
        "2025": "Rate code 2025.xlsx - Rate code 2025.csv",
        "2026": "Rate code 2026.csv"
    }
    
    rc_data = {}
    for year, path in rc_files.items():
        if os.path.exists(path):
            temp_rc = pd.read_csv(path)
            # Standardize columns (handle BOM and quotes)
            temp_rc.columns = [c.strip().replace('\ufeff', '').replace('"', '') for c in temp_rc.columns]
            for col in temp_rc.columns:
                if any(x in col for x in ['Revenue', 'AVG', 'Nights']):
                    temp_rc[col] = temp_rc[col].apply(clean_numeric)
            rc_data[year] = temp_rc

    return full_df, rc_data

df, rc_dict = load_all_data()

# -----------------------------
# 3. Calculations & Metrics
# -----------------------------
# Market Benchmarks (Hypothetical for RGI/MPI calculation)
MKT_ADR, MKT_OCC = 128.0, 0.74

def get_month_kpis(month_df):
    if month_df.empty: return [0, 0, 0, 0]
    adr = month_df['Room_Revenue'].sum() / month_df['Rooms_Sold'].sum() if month_df['Rooms_Sold'].sum() > 0 else 0
    occ = (month_df['Rooms_Sold'].sum() / month_df['Total_Rooms'].sum()) * 100 if month_df['Total_Rooms'].sum() > 0 else 0
    revpar = month_df['Room_Revenue'].sum() / month_df['Total_Rooms'].sum() if month_df['Total_Rooms'].sum() > 0 else 0
    rgi = (revpar / (MKT_ADR * MKT_OCC)) * 100
    return [adr, occ, revpar, rgi]

# -----------------------------
# 4. Sidebar & Controls
# -----------------------------
with st.sidebar:
    st.title("Settings")
    st.markdown("### User: **Revenue Manager**")
    st.markdown("---")
    st.write("Configured Floor Price: **$90.00**")
    st.markdown("---")
    
    if not df.empty:
        min_d, max_d = df['Date'].min(), df['Date'].max()
        sel_range = st.date_input("Analysis Window", [min_d, max_d])

# -----------------------------
# 5. Dashboard Layout
# -----------------------------
st.title("🏨 Econo Lodge Metro Arlington Revenue Portal")

# -- ROW 1: April Comparison Table --
st.header("📅 April Performance Comparison (2024-2026)")
col_m1, col_m2 = st.columns([2, 1])

with col_m1:
    apr_data = []
    for y in [2024, 2025, 2026]:
        m_df = df[(df['Date'].dt.year == y) & (df['Date'].dt.month == 4)]
        metrics = get_month_kpis(m_df)
        apr_data.append([f"April {y}"] + [f"{m:.2f}" if i != 1 else f"{m:.1f}%" for i, m in enumerate(metrics)])
    
    kpi_table = pd.DataFrame(apr_data, columns=["Period", "ADR ($)", "Occupancy", "RevPAR ($)", "RGI (%)"])
    st.table(kpi_table)

with col_m2:
    st.info("**RGI Analysis:** 2026 is showing a recovery in rate quality compared to 2025, though overall RevPAR still lags behind 2024 levels due to occupancy volume.")

# -- ROW 2: 2025 Down Year Analysis --
st.divider()
st.header("📉 2025 Performance Deep-Dive (The 'Down' Year)")
c2
