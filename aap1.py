import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Set page config
st.set_page_config(page_title="Hotel KPI Dashboard - Econo Lodge Metro", layout="wide")

# Constants
TOTAL_ROOMS = 47
ESTIMATED_GOP_MARGIN = 0.40  # 40% margin for economy hotels

@st.cache_data
def load_data():
    files = {
        '2023': 'APRIL 2023.csv',
        '2024': 'APRIL 2024.csv',
        '2025': 'APRIL 2025.csv',
        '2026': 'APRIL 2026.csv'
    }
    
    all_data = []
    for year, file in files.items():
        df = pd.read_csv(file)
        # Handle potential BOM in column names
        df.columns = [c.replace('\ufeff', '') for c in df.columns]
        
        # Data Cleaning
        df['Date'] = pd.to_datetime(df['IDS_DATE'])
        df['RoomRev'] = df['RoomRev'].str.replace(',', '').astype(float)
        df['OccPercent'] = df['OccPercent'].str.replace('%', '').astype(float)
        
        # Calculate Estimated GOP and GOPPAR
        df['Est_GOP'] = df['RoomRev'] * ESTIMATED_GOP_MARGIN
        df['GOPPAR'] = df['Est_GOP'] / df['Rooms']
        
        df['Year'] = year
        all_data.append(df)
        
    return pd.concat(all_data)

# Load data
try:
    df_full = load_data()
    df_full['Day_of_Month'] = df_full['Date'].dt.day
except Exception as e:
    st.error(f"Error loading data: {e}. Ensure CSV files are in the same directory.")
    st.stop()

# Sidebar
st.sidebar.header("Dashboard Filters")
selected_years = st.sidebar.multiselect("Select Years to Compare", ['2023', '2024', '2025', '2026'], default=['2024', '2025', '2026'])
gop_margin = st.sidebar.slider("Adjust Estimated GOP Margin (%)", 20, 60, 40) / 100

# Update GOPPAR based on slider
df_full['Est_GOP'] = df_full['RoomRev'] * gop_margin
df_full['GOPPAR'] = df_full['Est_GOP'] / df_full['Rooms']

# Title
st.title("🏨 Econo Lodge Metro - April KPI Performance")
st.markdown(f"**Location:** Arlington, VA | **Analysis Period:** April 2023 - 2026")
if '2026' in selected_years:
    st.info("Note: April 2026 is currently in progress. Data after April 11 represents future bookings.")

# Main KPIs
cols = st.columns(4)
latest_year = '2026' if '2026' in selected_years else max(selected_years)
current_df = df_full[df_full['Year'] == latest_year]

with cols[0]:
    st.metric("Avg Occ %", f"{current_df['OccPercent'].mean():.1f}%")
with cols[1]:
    st.metric("Avg ADR", f"${current_df['ADR'].mean():.2L}")
with cols[2]:
    st.metric("Avg RevPAR", f"${current_df['RevPAR'].mean():.2L}")
with cols[3]:
    st.metric("Avg GOPPAR (Est.)", f"${current_df['GOPPAR'].mean():.2L}")

# Trend Analysis
st.subheader("Daily KPI Trends")
metric_choice = st.selectbox("Select Metric", ["RevPAR", "ADR", "OccPercent", "GOPPAR"])

filtered_df = df_full[df_full['Year'].isin(selected_years)]
fig_trend = px.line(filtered_df, x='Day_of_Month', y=metric_choice, color='Year',
              title=f"April {metric_choice} Trends",
              labels={'Day_of_Month': 'Day of April', metric_choice: metric_choice},
              template="plotly_white")
st.plotly_chart(fig_trend, use_container_width=True)

# GOPPAR vs RevPAR Analysis
st.subheader("GOPPAR vs RevPAR Correlation")
col_a, col_b = st.columns(2)

with col_a:
    fig_scatter = px.scatter(filtered_df, x='RevPAR', y='GOPPAR', color='Year', 
                             title="Efficiency: RevPAR vs GOPPAR",
                             trendline="ols")
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_b:
    summary = filtered_df.groupby('Year').agg({
        'RoomRev': 'sum',
        'Est_GOP': 'sum',
        'RevPAR': 'mean',
        'GOPPAR': 'mean'
    }).reset_index()
    st.write("### Monthly Totals")
    st.dataframe(summary.style.format({
        'RoomRev': '${:,.2f}',
        'Est_GOP': '${:,.2f}',
        'RevPAR': '${:.2f}',
        'GOPPAR': '${:.2f}'
    }))

# Business Insight
st.subheader("Key Observations")
st.write("""
- **GOPPAR Sensitivity:** At a 40% margin, your GOPPAR tracks closely with RevPAR. Maintaining high ADR is critical for GOPPAR because variable costs (housekeeping/laundry) are higher when occupancy is the primary driver of revenue.
- **April 2026 Progress:** You can see a sharp drop-off in the trend charts after the current date; this is your window to push last-minute sales or adjust rates to fill the remaining nights.
""")
