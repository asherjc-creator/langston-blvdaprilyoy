import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime, timedelta
import os

# -----------------------------
# Helper Functions
# -----------------------------
def get_image_base64(image_path):
    """Loads an image and converts it to a base64 string for HTML embed."""
    try:
        if os.path.exists(image_path):
            img = Image.open(image_path)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
    except Exception:
        pass
    return ""

# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="Econo Lodge Arlington Revenue Portal",
    layout="wide",
    page_icon="🏨"
)

# -----------------------------
# Custom Styling
# -----------------------------
st.markdown("""
<style>
.main { background-color:#f5f7f9; }
.stMetric {
    background-color:white;
    padding:15px;
    border-radius:10px;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
}
[data-testid="stSidebar"] { background-color: #ffffff; }
[data-testid="stSidebar"] .stMarkdown { text-align: center; }
.title-container {
    display: flex;
    align-items: center;
    gap: 20px;
    margin-bottom: 20px;
}
.event-card {
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 10px;
    border-left: 5px solid #007bff;
    background: #ffffff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Data Loading & Cleaning
# -----------------------------
@st.cache_data
def load_all_data():
    # 1. Load Internal Econo Lodge Data
    files = ["ECONO - 2023.csv", "ECONO - 2024.csv", "ECONO - 2025.csv", "ECONO - 2026.csv"]
    df_list = []
    
    for file in files:
        if os.path.exists(file):
            temp_df = pd.read_csv(file)
            df_list.append(temp_df)
            
    if df_list:
        df = pd.concat(df_list, ignore_index=True)
        # Rename columns to match the dashboard logic
        df = df.rename(columns={
            "IDS_DATE": "Date", 
            "RoomRev": "Room_Revenue", 
            "Occupied": "Rooms_Sold", 
            "Rooms": "Total_Rooms",
            "OccPercent": "Occupancy_Str"
        })
        
        # Clean Date
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df.dropna(subset=["Date"])
        
        # Clean numeric fields (removing commas and converting types)
        for col in ["Room_Revenue", "ADR", "RevPAR"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('$', '').astype(float)
        
        # Ensure rooms sold/total rooms are numeric
        df["Rooms_Sold"] = pd.to_numeric(df["Rooms_Sold"], errors='coerce').fillna(0)
        df["Total_Rooms"] = pd.to_numeric(df["Total_Rooms"], errors='coerce').fillna(47)
        
        # Add Geographic data for Arlington Econo Lodge
        df["Lat"] = 38.8856
        df["Lon"] = -77.1664
        
    else:
        # Emergency Fallback if files aren't found
        st.error("No Econo Lodge data files found! Creating dummy data.")
        dates = pd.date_range(start="2023-01-01", periods=1000)
        df = pd.DataFrame({
            "Date": dates,
            "Room_Revenue": np.random.randint(1000, 5000, len(dates)),
            "Rooms_Sold": np.random.randint(15, 47, len(dates)),
            "Total_Rooms": [47]*len(dates),
            "Lat": [38.8856]*len(dates),
            "Lon": [-77.1664]*len(dates)
        })

    # Core Performance Metrics recalculation to ensure consistency
    df["ADR"] = np.where(df["Rooms_Sold"] > 0, df["Room_Revenue"] / df["Rooms_Sold"], 0)
    df["Occupancy"] = df["Rooms_Sold"] / df["Total_Rooms"]
    df["RevPAR"] = df["Room_Revenue"] / df["Total_Rooms"]

    # 2. Simulate Competitor Rates & Market Data (since no file was provided)
    # Give a ~10% standard deviation compared to Econo Lodge
    df["Market_Occ"] = df["Occupancy"] * np.random.uniform(0.85, 1.15, len(df))
    df["Market_Occ"] = df["Market_Occ"].clip(0, 1) # Max 100%
    df["Market_ADR"] = df["ADR"] * np.random.uniform(0.9, 1.2, len(df))
    
    df["MPI"] = np.where(df["Market_Occ"] > 0, (df["Occupancy"] / df["Market_Occ"]) * 100, 100)
    df["RGI"] = np.where((df["Market_ADR"] * df["Market_Occ"]) > 0, 
                         (df["RevPAR"] / (df["Market_ADR"] * df["Market_Occ"])) * 100, 100)

    # Creating a synthetic comp set for the competitor graph
    all_dates = pd.date_range(start=df["Date"].min(), end=df["Date"].max() + timedelta(days=90))
    comp = pd.DataFrame({
        "Date": all_dates,
        "Hotel": ["Arlington Benchmark"] * len(all_dates),
        "Rate": np.random.uniform(60, 130, len(all_dates))
    })

    # 3. Simulate DC/Arlington Events
    event_dates = all_dates[np.random.choice(len(all_dates), 30, replace=False)]
    events = pd.DataFrame({
        "Date": event_dates,
        "Event": ["DC Metro Convention", "Arlington Marathon", "Cherry Blossom Festival", "Capitol Tech Expo"] * 7 + ["Inauguration Week", "Trade Summit"],
        "Impact_Level": np.random.choice(["High", "Medium", "Low"], 30, p=[0.2, 0.5, 0.3])
    })
    
    return df, comp, events

df, comp, events = load_all_data()

# -----------------------------
# Sidebar Profile & Control
# -----------------------------
asher_pic_base64 = get_image_base64("asher_picture.png")
github_url = "https://github.com/asherjc-creator/econo-revenue-dashboard"

with st.sidebar:
    if asher_pic_base64:
        st.markdown(f'<img src="{asher_pic_base64}" style="border-radius: 50%; width: 140px; height: 140px; object-fit: cover; display: block; margin: 0 auto 10px auto; border: 3px solid #eee;">', unsafe_allow_html=True)

    st.markdown("## Asher Jannu")
    st.markdown("### **Revenue Analyst**")
    st.markdown(f'<a href="{github_url}" target="_blank"><button style="background-color: #24292e; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; width: 100%;">View GitHub Code</button></a>', unsafe_allow_html=True)
    st.markdown("---")
    
    st.header("Control Panel")
    date_range = st.date_input("Select Date Range", [df["Date"].min(), df["Date"].max()])
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range[0]

# Filter Data based on Sidebar
filtered = df[(df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))]
comp_filtered = comp[(comp["Date"] >= pd.to_datetime(start_date)) & (comp["Date"] <= pd.to_datetime(end_date))]

# -----------------------------
# Header / Title Section
# -----------------------------
logo_base64 = get_image_base64("logo.png")
if logo_base64:
    st.markdown(f'<div class="title-container"><img src="{logo_base64}" style="width: 120px;"><div style="flex-grow: 1;"><h1 style="margin: 0; color: #333;">Econo Lodge Metro Arlington</h1><h3 style="margin: 0; color: #666; font-weight: normal;">Revenue Management Dashboard</h3></div></div>', unsafe_allow_html=True)
else:
    st.title("🏨 Econo Lodge Metro Arlington | Revenue Dashboard")

# -----------------------------
# KPI Metrics Row
# -----------------------------
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Average ADR", f"${filtered['ADR'].mean():.2f}")
kpi2.metric("Occupancy", f"{filtered['Occupancy'].mean()*100:.1f}%")
kpi3.metric("RevPAR", f"${filtered['RevPAR'].mean():.2f}")
kpi4.metric("Market Share (RGI)", f"{filtered['RGI'].mean():.1f}")

# -----------------------------
# Main Charts
# -----------------------------
c1, c2 = st.columns(2)
with c1:
    st.write("### RevPAR Trend")
    
    # We use make_subplots to allow two different Y-axis scales
    from plotly.subplots import make_subplots
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Add Room Revenue (Primary Y-Axis - Left)
    fig.add_trace(
        go.Scatter(
            x=filtered["Date"], 
            y=filtered["Room_Revenue"], 
            name="Room Revenue ($)",
            line=dict(color='#1f77b4', width=3)
        ),
        secondary_y=False,
    )

    # 2. Add RevPAR (Secondary Y-Axis - Right)
    fig.add_trace(
        go.Scatter(
            x=filtered["Date"], 
            y=filtered["RevPAR"], 
            name="RevPAR ($)",
            line=dict(color='#ff7f0e', width=3)
        ),
        secondary_y=True,
    )

    # Update layout to show both labels
    fig.update_layout(
        title_text="RevPAR Performance",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="<b>Total Revenue</b> ($)", secondary_y=False)
    fig.update_yaxes(title_text="<b>RevPAR</b> ($)", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.write("### Market Penetration (MPI)")
    fig2 = px.bar(filtered, x="Date", y="MPI", color="MPI", color_continuous_scale="RdYlGn", title="Occupancy vs. Market Average")
    st.plotly_chart(fig2, use_container_width=True)

st.write("### Competitor Rate Benchmarking")
fig_comp = px.line(comp_filtered, x="Date", y="Rate", color="Hotel", title="Direct Competitor Daily Rates")
st.plotly_chart(fig_comp, use_container_width=True)

# -----------------------------
# 📈 90-Day Predictive Analysis
# -----------------------------
st.write("---")
st.header("📈 90-Day Forecast & Predictive Pricing")

# Prediction logic
last_data_date = df["Date"].max()
future_dates = pd.date_range(start=last_data_date + timedelta(days=1), periods=90)

# Use competitor averages as a future baseline
try:
    future_baseline = comp[comp["Date"].isin(future_dates)].groupby("Date")["Rate"].mean().reindex(future_dates).ffill().fillna(df["ADR"].mean())
except Exception:
    future_baseline = pd.Series([df["ADR"].mean()]*90, index=future_dates)

forecast_df = pd.DataFrame({"Date": future_dates, "Market_Baseline": future_baseline.values})
forecast_df = forecast_df.merge(events, on="Date", how="left").fillna({"Impact_Level": "None", "Event": "No Major Event"})

# Weighting Logic
multipliers = {"High": 1.25, "Medium": 1.12, "Low": 1.05, "None": 1.0}
forecast_df["Predicted_Rate"] = forecast_df.apply(lambda x: x["Market_Baseline"] * multipliers[x["Impact_Level"]], axis=1)

# Forecast Chart
fig_forecast = go.Figure()
fig_forecast.add_trace(go.Scatter(x=forecast_df["Date"], y=forecast_df["Predicted_Rate"], name="AI Suggested Rate", line=dict(color='#2ca02c', width=4)))
fig_forecast.add_trace(go.Scatter(x=forecast_df["Date"], y=forecast_df["Market_Baseline"], name="Market Baseline", line=dict(dash='dash', color='gray')))

# Annotate Top Events on Chart
high_impact = forecast_df[forecast_df["Impact_Level"] == "High"]
for idx, row in high_impact.iterrows():
    fig_forecast.add_annotation(x=row["Date"], y=row["Predicted_Rate"], text=row["Event"], showarrow=True, arrowhead=1)

st.plotly_chart(fig_forecast, use_container_width=True)

# -----------------------------
# Heatmaps Section
# -----------------------------
st.write("### 📅 Pricing & Demand Heatmaps")
h_col1, h_col2 = st.columns(2)

with h_col1:
    st.write("#### Temporal Rate Intensity")
    forecast_df['Weekday'] = forecast_df['Date'].dt.day_name()
    forecast_df['Week'] = forecast_df['Date'].dt.isocalendar().week
    pivot = forecast_df.pivot_table(index='Weekday', columns='Week', values='Predicted_Rate')
    # Ensure correct day order
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])
    
    fig_h = px.imshow(pivot, color_continuous_scale="YlOrRd", labels=dict(color="Rate ($)"))
    st.plotly_chart(fig_h, use_container_width=True)

with h_col2:
    st.write("#### Guest Origin (Geographic Heatmap)")
    # Econo Lodge Coordinates for plotting point
    m_heat = folium.Map(location=[38.8856, -77.1664], zoom_start=13)
    heat_data = df[["Lat","Lon"]].dropna().values.tolist()
    
    # Adding a specific marker for the Hotel
    folium.Marker([38.8856, -77.1664], popup="Econo Lodge Arlington", icon=folium.Icon(color="blue", icon="info-sign")).add_to(m_heat)
    HeatMap(heat_data).add_to(m_heat)
    st_folium(m_heat, width=600, height=350)

# -----------------------------
# AI Engine & Events Feed
# -----------------------------
st.write("---")
f_col1, f_col2 = st.columns([2, 1])

with f_col1:
    st.write("### 🤖 AI Pricing Recommendation Engine")
    check_date = st.date_input("Query a Specific Future Date:", last_data_date + timedelta(days=7))
    target_row = forecast_df[forecast_df["Date"] == pd.to_datetime(check_date)]
    
    if not target_row.empty:
        row = target_row.iloc[0]
        rec_price = row["Predicted_Rate"]
        base = row["Market_Baseline"]
        event = row["Event"]
        impact = row["Impact_Level"]
        
        st.metric(f"Recommended ADR for {check_date.strftime('%b %d')}", f"${rec_price:.0f}", 
                  delta=f"{((rec_price/base)-1)*100:.1f}% Yield Increase")
        
        if impact != "None":
            st.info(f"**Event Factor:** {event} is driving high demand ({impact} Impact).")
        else:
            st.write("Recommendation based on standard market trends.")
    else:
        st.warning("Selected date is outside the 90-day forecast range.")

with f_col2:
    st.write("### 🚩 Upcoming DC/Arlington Events")
    upcoming = events[events["Date"] >= pd.to_datetime(datetime.now())].sort_values("Date").head(5)
    if upcoming.empty:
        st.write("No upcoming events found in database.")
    else:
        for _, row in upcoming.iterrows():
            st.markdown(f"""
            <div class="event-card">
                <strong>{row['Date'].strftime('%b %d, %Y')}</strong><br>
                {row['Event']} <br>
                <span style="color: {'#d9534f' if row['Impact_Level'] == 'High' else '#f0ad4e'}; font-weight: bold;">
                    Impact: {row['Impact_Level']}
                </span>
            </div>
            """, unsafe_allow_html=True)
