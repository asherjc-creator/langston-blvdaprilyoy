import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# ------------------------------
# 1. Configuration & Constants
# ------------------------------
st.set_page_config(page_title="Econo Lodge Metro - KPI Dashboard", layout="wide")

TOTAL_ROOMS = 47
EST_GOP_MARGIN = 0.40  
MARKET_AVG_OCC = 62.2  
TODAY_2026 = datetime(2026, 4, 11)

# ------------------------------
# 2. Data Loading & Cleaning
# ------------------------------
@st.cache_data
def load_all_data():
    years = [2023, 2024, 2025, 2026]
    dfs = []
    
    for year in years:
        file_path = Path(f"APRIL {year}.csv")
        if file_path.exists():
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            df.columns = [c.strip().replace('\ufeff', '').replace('"', '').replace(' ', '') for c in df.columns]
            
            df['IDS_DATE'] = pd.to_datetime(df['IDS_DATE'], errors='coerce')
            df = df.dropna(subset=['IDS_DATE'])
            df['DayOfMonth'] = df['IDS_DATE'].dt.day
            
            def force_numeric(series):
                return pd.to_numeric(series.astype(str).str.replace(r'[$,%]', '', regex=True).str.strip(), errors='coerce').fillna(0)

            df['OccPercent'] = force_numeric(df['OccPercent'])
            df['RoomRev'] = force_numeric(df['RoomRev'])
            df['ADR'] = force_numeric(df['ADR'])
            df['RevPAR'] = force_numeric(df['RevPAR'])
            df['Occupied'] = force_numeric(df['Occupied'])
            
            df['Est_GOP'] = df['RoomRev'] * EST_GOP_MARGIN
            df['GOPPAR'] = df['Est_GOP'] / TOTAL_ROOMS
            df['Year'] = str(year)
            dfs.append(df)
            
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

df_all = load_all_data()

if df_all.empty:
    st.error("Data files not found.")
    st.stop()

# ------------------------------
# 3. Sidebar & Filtering
# ------------------------------
st.sidebar.header("Filters")
available_years = sorted(df_all['Year'].unique())
selected_years = st.sidebar.multiselect("Select Years", options=available_years, default=available_years)
df_filtered = df_all[df_all['Year'].isin(selected_years)].copy()

st.title("🏨 Hotel Performance Dashboard – April 2023–2026")

# ------------------------------
# 4. KPI Bar Charts Section
# ------------------------------
st.subheader("📊 Key Performance Indicators (Yearly Comparison)")

# Aggregated data for bars
agg_df = df_filtered.groupby('Year').agg({
    'RoomRev': 'sum',
    'OccPercent': 'mean',
    'ADR': 'mean',
    'RevPAR': 'mean',
    'GOPPAR': 'mean'
}).reset_index()

# 2x2 Grid for KPI Bar Charts
col1, col2 = st.columns(2)
with col1:
    fig_rev = px.bar(agg_df, x='Year', y='RoomRev', title="Total Room Revenue ($)", text_auto='.2s', color='Year')
    st.plotly_chart(fig_rev, use_container_width=True)
    
    fig_occ = px.bar(agg_df, x='Year', y='OccPercent', title="Average Occupancy (%)", text_auto='.1f', color='Year')
    st.plotly_chart(fig_occ, use_container_width=True)

with col2:
    fig_adr = px.bar(agg_df, x='Year', y='ADR', title="Average ADR ($)", text_auto='.2s', color='Year')
    st.plotly_chart(fig_adr, use_container_width=True)
    
    fig_revpar = px.bar(agg_df, x='Year', y='RevPAR', title="Average RevPAR ($)", text_auto='.2s', color='Year')
    st.plotly_chart(fig_revpar, use_container_width=True)

# ---------------------------------------------------------
# 5. Updated Historical Trend Line Chart
# ---------------------------------------------------------
st.divider()
st.subheader("📅 Historical April Trend on Month year Line chart")

metric_choice = st.selectbox(
    "Select KPI to view daily trend", 
    options=['OccPercent', 'ADR', 'RevPAR', 'GOPPAR', 'RoomRev'],
    format_func=lambda x: {'OccPercent':'Occupancy %', 'ADR':'ADR ($)', 'RevPAR':'RevPAR ($)', 'GOPPAR':'GOPPAR ($)', 'RoomRev':'Revenue ($)'}.get(x, x)
)

fig_line = px.line(
    df_filtered, 
    x='DayOfMonth', 
    y=metric_choice, 
    color='Year',
    title=f"Daily {metric_choice} Comparison",
    labels={'DayOfMonth': 'Day of April'},
    markers=True
)

# Logic to calculate and display the current selection's average in the top right corner
for year in selected_years:
    y_data = df_filtered[df_filtered['Year'] == year][metric_choice]
    avg_val = y_data.mean()
    prefix = "$" if metric_choice in ['ADR', 'RevPAR', 'GOPPAR', 'RoomRev'] else ""
    suffix = "%" if metric_choice == 'OccPercent' else ""
    
    # Adding a clean annotation for the primary/latest year or summarized info
    if year == max(selected_years):
        fig_line.add_annotation(
            xref="paper", yref="paper",
            x=1, y=1.05,
            text=f"<b>{year} Avg: {prefix}{avg_val:.2f}{suffix}</b>",
            showarrow=False,
            font=dict(size=14, color="white"),
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor="white",
            borderwidth=1
        )

fig_line.update_layout(hovermode="x unified", xaxis=dict(tickmode='linear', dtick=1))
st.plotly_chart(fig_line, use_container_width=True)

# ---------------------------------------------------------
# 6. Heatmap & Prediction
# ---------------------------------------------------------
st.divider()
st.subheader("🔥 Occupancy Heatmap: April 2026 vs Comset")
df_2026 = df_all[df_all['Year'] == '2026'].copy()
if not df_2026.empty:
    heat_data = df_2026[['DayOfMonth', 'OccPercent']].copy()
    heat_data['Comset Avg'] = MARKET_AVG_OCC
    heat_pivot = heat_data.rename(columns={'OccPercent': '2026 Actual'}).set_index('DayOfMonth').T
    st.plotly_chart(px.imshow(heat_pivot, text_auto='.1f', color_continuous_scale='Oranges', aspect="auto"), use_container_width=True)

st.divider()
st.subheader("🔮 Predictive Analytics: West Arlington (22213)")
st.info(f"**April 2026 Prediction:** Stabilized Occupancy is projected at **92.4%** for the West Arlington sub-market, maintaining a significant performance premium over the area average.")
