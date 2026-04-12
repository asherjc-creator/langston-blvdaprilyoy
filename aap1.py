import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# ------------------------------
# Page config & Constants
# ------------------------------
st.set_page_config(page_title="Hotel Performance Dashboard", layout="wide")
st.title("🏨 Hotel Performance Dashboard – April 2023–2026")

TOTAL_ROOMS = 47
EST_GOP_MARGIN = 0.40  # 40% margin for Econo Lodge Metro Arlington
TODAY_2026 = datetime(2026, 4, 11)

# ------------------------------
# Helper functions
# ------------------------------
@st.cache_data
def load_all_data():
    """Load all April CSV files and return a single DataFrame with a 'Year' column."""
    years = [2023, 2024, 2025, 2026]
    dfs = []
    for year in years:
        file_path = Path(f"APRIL {year}.csv")
        if file_path.exists():
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # Clean column names
            df.columns = (
                df.columns
                .str.strip()
                .str.replace('"', '', regex=False)
                .str.replace(' ', '', regex=False)
                .str.replace('﻿', '', regex=False)
            )
            
            if 'IDS_DATE' not in df.columns:
                for col in df.columns:
                    if col.upper() == 'IDS_DATE':
                        df.rename(columns={col: 'IDS_DATE'}, inplace=True)
                        break
            
            if 'IDS_DATE' in df.columns:
                df['IDS_DATE'] = pd.to_datetime(df['IDS_DATE'], errors='coerce')
            else:
                continue
            
            # Data Cleaning for KPIs
            if 'OccPercent' in df.columns:
                df['OccPercent'] = df['OccPercent'].astype(str).str.replace('%', '', regex=False).str.strip()
                df['OccPercent'] = pd.to_numeric(df['OccPercent'], errors='coerce')
            
            numeric_cols = ['RoomRev', 'RevPAR', 'ADR', 'Occupied', 'Available', 'Rooms']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # GOPPAR Estimation (Requirement: Arlington Econo Lodge)
            df['Est_GOP'] = df['RoomRev'] * EST_GOP_MARGIN
            df['GOPPAR'] = df['Est_GOP'] / TOTAL_ROOMS
            
            df['Year'] = year
            dfs.append(df)
    
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def compute_kpis(df):
    """Return a dictionary of aggregated KPIs."""
    # For 2026, we only look at data up to April 11 to keep averages accurate
    mask_2026 = (df['Year'] == 2026) & (df['IDS_DATE'] <= TODAY_2026)
    mask_others = (df['Year'] != 2026)
    display_df = pd.concat([df[mask_2026], df[mask_others]])

    return {
        'Total Revenue': f"${display_df['RoomRev'].sum():,.0f}",
        'Avg Occupancy': f"{display_df['OccPercent'].mean():.1f}%",
        'Avg ADR': f"${display_df['ADR'].mean():.2f}",
        'Avg RevPAR': f"${display_df['RevPAR'].mean():.2f}",
        'Avg GOPPAR (Est)': f"${display_df['GOPPAR'].mean():.2f}"
    }

# ------------------------------
# Load data
# ------------------------------
df_all = load_all_data()
if df_all.empty:
    st.error("No data files found.")
    st.stop()

# ------------------------------
# Sidebar filters
# ------------------------------
st.sidebar.header("Filters")
available_years = sorted(df_all['Year'].unique())
selected_years = st.sidebar.multiselect("Select Years", options=available_years, default=available_years)

df_filtered = df_all[df_all['Year'].isin(selected_years)].copy()

# ------------------------------
# Main dashboard
# ------------------------------
st.subheader(f"📊 Key Metrics Comparison")
kpis = compute_kpis(df_filtered)
cols = st.columns(len(kpis))
for col, (label, value) in zip(cols, kpis.items()):
    col.metric(label, value)

# ---- Bar Charts ----
agg_df = df_filtered.groupby('Year').agg({
    'RoomRev': 'sum',
    'OccPercent': 'mean',
    'ADR': 'mean',
    'RevPAR': 'mean',
    'GOPPAR': 'mean'
}).reset_index()

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(px.bar(agg_df, x='Year', y='RevPAR', title="RevPAR by Year", color='Year', text_auto='.2s'), use_container_width=True)
with c2:
    st.plotly_chart(px.bar(agg_df, x='Year', y='GOPPAR', title="Estimated GOPPAR by Year", color='Year', text_auto='.2s'), use_container_width=True)

# ------------------------------------------------------------------
# CHANGED SECTION: Historical April Trend on Month year Line chart
# ------------------------------------------------------------------
st.subheader("📅 Historical April Trend on Month year Line chart")

# Dropdown label changed to APRIL-Year
available_years_trend = sorted(df_filtered['Year'].unique())
selected_trend_year = st.selectbox("APRIL-Year", options=available_years_trend)

# Metric Selector
metric_choice = st.selectbox("Select metric to view daily trend",
                             options=['OccPercent', 'ADR', 'RevPAR', 'GOPPAR', 'RoomRev'],
                             format_func=lambda x: {
                                 'OccPercent': 'Occupancy %',
                                 'ADR': 'ADR ($)',
                                 'RevPAR': 'RevPAR ($)',
                                 'GOPPAR': 'GOPPAR ($)',
                                 'RoomRev': 'Room Revenue ($)'
                             }.get(x, x))

df_trend = df_filtered[df_filtered['Year'] == selected_trend_year].copy()

if not df_trend.empty:
    fig_line = px.line(df_trend, x='IDS_DATE', y=metric_choice,
                       title=f"Daily {metric_choice} – April {selected_trend_year}",
                       labels={'IDS_DATE': 'Date'})
    # Add vertical line for "Today" if looking at 2026
    if selected_trend_year == 2026:
        fig_line.add_vline(x=TODAY_2026, line_dash="dash", line_color="red", annotation_text="Today")
    
    fig_line.update_layout(hovermode='x unified')
    st.plotly_chart(fig_line, use_container_width=True)

# ------------------------------------------------------------------
# Heatmap & Insights
# ------------------------------------------------------------------
st.subheader("🔥 Occupancy Heatmap (Day vs Year)")
df_filtered['DayOfMonth'] = df_filtered['IDS_DATE'].dt.day
pivot = df_filtered.pivot_table(index='DayOfMonth', columns='Year', values='OccPercent', aggfunc='mean')
st.plotly_chart(px.imshow(pivot, text_auto='.1f', aspect="auto", color_continuous_scale='Oranges'), use_container_width=True)

with st.expander("📋 View Raw Data"):
    st.dataframe(df_filtered.sort_values('IDS_DATE'), use_container_width=True)

st.caption("Data source: April 2023–2026 CSV files for Econo Lodge Metro Arlington.")
