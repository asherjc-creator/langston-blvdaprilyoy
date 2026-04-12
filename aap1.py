import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Set page config
st.set_page_config(page_title="Hotel KPI Dashboard - Econo Lodge Metro", layout="wide")

# Constants
TOTAL_ROOMS = 47
ESTIMATED_GOP_MARGIN = 0.40  # 40% margin for economy hotels
TODAY = datetime(2026, 4, 11)  # Setting "today" as April 11, 2026 per data context

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
        try:
            df = pd.read_csv(file)
            # Handle potential BOM in column names
            df.columns = [c.replace('\ufeff', '') for c in df.columns]
            
            # Data Cleaning
            df['Date'] = pd.to_datetime(df['IDS_DATE'])
            
            # Clean RoomRev: Handle strings with commas and convert to float
            if df['RoomRev'].dtype == 'object':
                df['RoomRev'] = df['RoomRev'].str.replace(',', '').str.strip()
                df['RoomRev'] = pd.to_numeric(df['RoomRev'], errors='coerce').fillna(0)
            
            # Ensure OccPercent is numeric
            if df['OccPercent'].dtype == 'object':
                df['OccPercent'] = df['OccPercent'].str.replace('%', '').str.strip()
                df['OccPercent'] = pd.to_numeric(df['OccPercent'], errors='coerce').fillna(0)
            
            # Calculate Estimated GOP and GOPPAR
            df['Est_GOP'] = df['RoomRev'] * ESTIMATED_GOP_MARGIN
            df['GOPPAR'] = df['Est_GOP'] / TOTAL_ROOMS
            
            df['Year'] = year
            all_data.append(df)
        except Exception as e:
            st.error(f"Error processing {file}: {e}")
            
    return pd.concat(all_data)

# Load data
df_full = load_data()
df_full['Day_of_Month'] = df_full['Date'].dt.day

# Sidebar
st.sidebar.header("Dashboard Settings")
selected_years = st.sidebar.multiselect("Compare Years", ['2023', '2024', '2025', '2026'], default=['2024', '2025', '2026'])
gop_margin = st.sidebar.slider("Est. GOP Margin (%)", 20, 60, 40) / 100

# Update GOP based on slider
df_full['Est_GOP'] = df_full['RoomRev'] * gop_margin
df_full['GOPPAR'] = df_full['Est_GOP'] / TOTAL_ROOMS

# Title
st.title("🏨 Econo Lodge Metro - KPI Analysis")
st.markdown(f"**Location:** Arlington, VA | **Analysis Period:** April Year-Over-Year")

if '2026' in selected_years:
    st.warning(f"⚠️ **April 2026 Status:** Data after {TODAY.strftime('%B %d')} represents 'On the Books' (OTB) future bookings, not finalized actuals.")

# Metric Calculation for Selected Years
latest_year = '2026' if '2026' in selected_years else max(selected_years)
current_df = df_full[df_full['Year'] == latest_year]

# Use Actuals Only for 2026 Metrics to avoid diluting averages with incomplete data
if latest_year == '2026':
    metric_df = current_df[current_df['Date'] <= TODAY]
else:
    metric_df = current_df

cols = st.columns(4)
with cols[0]:
    st.metric("Avg Occ %", f"{metric_df['OccPercent'].mean():.1f}%")
with cols[1]:
    # FIXED: Changed :.2L to :.2f
    st.metric("Avg ADR", f"${metric_df['ADR'].mean():.2f}")
with cols[2]:
    st.metric("Avg RevPAR", f"${metric_df['RevPAR'].mean():.2f}")
with cols[3]:
    st.metric("Avg GOPPAR (Est.)", f"${metric_df['GOPPAR'].mean():.2f}")

# Trend Analysis
st.subheader("Daily Trends Comparison")
metric_choice = st.selectbox("Select Metric", ["RevPAR", "ADR", "OccPercent", "GOPPAR"])

filtered_df = df_full[df_full['Year'].isin(selected_years)]
fig_trend = px.line(filtered_df, x='Day_of_Month', y=metric_choice, color='Year',
              title=f"April {metric_choice} Trends (Daily)",
              labels={'Day_of_Month': 'Day of April'},
              template="plotly_white")

# Add a vertical line for "Today" if 2026 is visible
if '2026' in selected_years:
    fig_trend.add_vline(x=TODAY.day, line_dash="dash", line_color="red", annotation_text="Today")

st.plotly_chart(fig_trend, use_container_width=True)

# Efficiency Table
st.subheader("Monthly Performance Summary")
summary = filtered_df.groupby('Year').agg({
    'RoomRev': 'sum',
    'Est_GOP': 'sum',
    'RevPAR': 'mean',
    'GOPPAR': 'mean'
}).reset_index()

st.table(summary.style.format({
    'RoomRev': '${:,.2f}',
    'Est_GOP': '${:,.2f}',
    'RevPAR': '${:.2f}',
    'GOPPAR': '${:.2f}'
}))
