import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Set page config
st.set_page_config(page_title="Econo Lodge Metro - KPI Dashboard", layout="wide")

# Constants
TOTAL_ROOMS = 47
ESTIMATED_GOP_MARGIN = 0.40
# Setting current date context for April 2026
CURRENT_DATE_2026 = datetime(2026, 4, 11) 

def clean_numeric(series):
    """Helper to force conversion of strings with commas/symbols to numbers."""
    if series.dtype == 'object':
        # Convert to string, remove commas, percent signs, and spaces
        series = series.astype(str).str.replace(r'[$,%]', '', regex=True).str.strip()
    return pd.to_numeric(series, errors='coerce').fillna(0)

@st.cache_data
def load_and_clean_data():
    files = {
        '2023': 'APRIL 2023.csv',
        '2024': 'APRIL 2024.csv',
        '2025': 'APRIL 2025.csv',
        '2026': 'APRIL 2026.csv'
    }
    
    all_data = []
    for year, file in files.items():
        try:
            # Load file
            df = pd.read_csv(file)
            
            # 1. Clean Column Names (Remove BOM, spaces, and hidden characters)
            df.columns = [c.replace('\ufeff', '').strip() for c in df.columns]
            
            # 2. Convert Date
            df['Date'] = pd.to_datetime(df['IDS_DATE'], errors='coerce')
            df = df.dropna(subset=['Date']) # Remove any empty rows
            
            # 3. Robustly convert all KPI columns to float
            df['RoomRev'] = clean_numeric(df['RoomRev'])
            df['OccPercent'] = clean_numeric(df['OccPercent'])
            df['ADR'] = clean_numeric(df['ADR'])
            df['RevPAR'] = clean_numeric(df['RevPAR'])
            df['Occupied'] = clean_numeric(df['Occupied'])
            
            # 4. Handle GOP calculations
            df['Est_GOP'] = df['RoomRev'] * ESTIMATED_GOP_MARGIN
            df['GOPPAR'] = df['Est_GOP'] / TOTAL_ROOMS
            
            df['Year'] = year
            all_data.append(df)
            
        except Exception as e:
            st.error(f"Error reading {file}: {e}")
            
    if not all_data:
        return pd.DataFrame()
        
    return pd.concat(all_data)

# App execution
df_full = load_and_clean_data()

if df_full.empty:
    st.error("Could not load any data. Please check your CSV file formats.")
    st.stop()

df_full['Day_of_Month'] = df_full['Date'].dt.day

# Sidebar
st.sidebar.header("Dashboard Controls")
selected_years = st.sidebar.multiselect("Select Years", ['2023', '2024', '2025', '2026'], default=['2024', '2025', '2026'])
gop_slider = st.sidebar.slider("Est. GOP Margin (%)", 20, 60, 40) / 100

# Recalculate based on slider
df_full['Est_GOP'] = df_full['RoomRev'] * gop_slider
df_full['GOPPAR'] = df_full['Est_GOP'] / TOTAL_ROOMS

# Title
st.title(" Econo Lodge Metro (Arlington, VA)")
st.subheader("April Year-Over-Year KPI Analysis")

# Metric Row
latest_year = '2026' if '2026' in selected_years else max(selected_years)
current_df = df_full[df_full['Year'] == latest_year]

# For 2026, only show metrics based on actuals (up to April 11)
if latest_year == '2026':
    display_df = current_df[current_df['Date'] <= CURRENT_DATE_2026]
    st.info(f"💡 Metrics for 2026 are based on actuals through {CURRENT_DATE_2026.strftime('%b %d')}.")
else:
    display_df = current_df

cols = st.columns(4)
with cols[0]:
    st.metric("Avg Occ %", f"{display_df['OccPercent'].mean():.1f}%")
with cols[1]:
    st.metric("Avg ADR", f"${display_df['ADR'].mean():.2f}")
with cols[2]:
    st.metric("Avg RevPAR", f"${display_df['RevPAR'].mean():.2f}")
with cols[3]:
    st.metric("Avg GOPPAR (Est.)", f"${display_df['GOPPAR'].mean():.2f}")

# Trend Graph
st.divider()
metric_to_plot = st.selectbox("Select Trend Metric", ["RevPAR", "GOPPAR", "ADR", "OccPercent"])

filtered_df = df_full[df_full['Year'].isin(selected_years)]
fig = px.line(filtered_df, x='Day_of_Month', y=metric_to_plot, color='Year',
              title=f"April {metric_to_plot} Daily Trends",
              labels={'Day_of_Month': 'Day of the Month'},
              template="plotly_dark")

# Visual marker for 2026 status
if '2026' in selected_years:
    fig.add_vline(x=CURRENT_DATE_2026.day, line_dash="dash", line_color="orange", 
                 annotation_text="Today (April 11)")

st.plotly_chart(fig, use_container_width=True)

# Comparison Table
st.subheader("Monthly Financial Performance Summary")
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
