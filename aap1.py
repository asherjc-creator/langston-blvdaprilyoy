import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime, timedelta
import os

# -----------------------------
# 1. Helper Functions
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

def clean_value(val):
    """Cleans currency, commas, percentages, and special characters from data."""
    if val is None or pd.isna(val):
        return 0.0
    val_str = str(val).replace(',', '').replace('$', '').replace('%', '').replace('"', '').strip()
    if val_str in ['∞', '', 'nan', 'None', '?', '-']:
        return 0.0
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def get_rate_mapping(file_path):
    """Maps rate codes to their respective categories."""
    if not os.path.exists(file_path):
        return {}
    try:
        df_raw = pd.read_csv(file_path, header=None)
        col_to_cat = {
            0: "Group", 1: "Wholesale", 2: "Opaque", 
            3: "Advance Purchase", 4: "Promotion",
            28: "OTA Bundle Package", 30: "Locked/Other"
        }
        mapping = {}
        for col_idx, cat_name in col_to_cat.items():
            if col_idx < len(df_raw.columns):
                codes = df_raw.iloc[4:, col_idx].dropna().tolist()
                for code in codes:
                    mapping[str(code).strip()] = cat_name
        return mapping
    except Exception:
        return {}

def generate_competitor_data(hotel_name, base_adr, volatility=0.12):
    """Generate synthetic competitor rate data for 2026."""
    dates = pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')
    seasonal = 1 + 0.2 * np.sin(2 * np.pi * (dates.dayofyear - 90) / 365)
    weekend_premium = np.where(dates.dayofweek >= 5, 1.15, 1.0)
    np.random.seed(abs(hash(hotel_name)) % 10000)
    noise = 1 + np.random.normal(0, volatility, len(dates))
    rates = base_adr * seasonal * weekend_premium * noise
    return pd.DataFrame({'Date': dates, 'Hotel': hotel_name, 'Rate': np.maximum(rates, 65).round(2)})

# -----------------------------
# 2. Page Configuration & Styling
# -----------------------------
st.set_page_config(page_title="Econo Lodge Arlington Revenue Portal", layout="wide", page_icon="🏨")

st.markdown("""
<style>
.main { background-color:#f5f7f9; }
.stMetric { background-color:white; padding:15px; border-radius:10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
.floor-price-banner {
    padding: 10px; background-color: #fff3cd; border: 1px solid #ffeeba;
    color: #856404; border-radius: 5px; text-align: center; font-weight: bold; margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 3. Data Loading
# -----------------------------
@st.cache_data
def load_all_data():
    rate_mapping = get_rate_mapping("my codes.csv")
    kpi_files = {"2023": "ECONO - 2023.csv", "2024": "ECONO - 2024.csv", "2025": "ECONO - 2025.csv", "2026": "ECONO - 2026.csv"}
    df_list = []
    
    for year, file in kpi_files.items():
        if os.path.exists(file):
            temp = pd.read_csv(file)
            temp.columns = [c.strip() for c in temp.columns]
            temp.rename(columns={'IDS_DATE': 'Date', 'RoomRev': 'Room_Revenue', 'Occupied': 'Rooms_Sold', 'Rooms': 'Total_Rooms', 'Arrivals': 'Arrivals'}, inplace=True)
            temp['Date'] = pd.to_datetime(temp['Date'], errors='coerce')
            temp = temp.dropna(subset=['Date'])
            
            numeric_cols = ['Room_Revenue', 'ADR', 'RevPAR', 'Rooms_Sold', 'Total_Rooms', 'Arrivals']
            for col in numeric_cols:
                if col in temp.columns:
                    temp[col] = temp[col].apply(clean_value)
            
            if 'Arrivals' not in temp.columns: temp['Arrivals'] = 0
            temp['Year'] = int(year)
            df_list.append(temp)

    full_df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
    if not full_df.empty:
        full_df['Occupancy'] = np.where(full_df['Total_Rooms'] > 0, full_df['Rooms_Sold'] / full_df['Total_Rooms'], 0.0)

    # Competitor & Event Logic
    events = pd.DataFrame({
        "Date": pd.to_datetime(["2026-04-12", "2026-04-13", "2026-04-14", "2026-05-15", "2026-07-04", "2026-09-20"]),
        "Event": ["Cherry Blossom Peak", "Cherry Blossom Peak", "Cherry Blossom Peak", "Tech Summit", "Independence Day", "Marine Marathon"],
        "Impact_Level": ["High", "High", "High", "Medium", "High", "Medium"],
        "Premium": [200, 200, 200, 0, 0, 0]
    })

    competitors = {"Econo Lodge Metro Arlington": 95, "Comfort Inn Ballston": 115, "Holiday Inn Express Arlington": 125, "Days Inn": 85, "Hyatt Place": 140}
    comp_df = pd.concat([generate_competitor_data(h, r) for h, r in competitors.items()], ignore_index=True)

    return full_df, comp_df, events, rate_mapping

df, competitor_df, events, rate_mapping = load_all_data()

# -----------------------------
# 4. Sidebar
# -----------------------------
with st.sidebar:
    st.title("Asher Jannu")
    st.subheader("Revenue Analyst")
    st.divider()
    
    if not df.empty:
        # FIX: Safety handling for date_range tuple length
        dr_input = st.date_input("Analysis Range", [df["Date"].min(), df["Date"].max()])
        if isinstance(dr_input, (list, tuple)) and len(dr_input) == 2:
            start_dt, end_dt = pd.to_datetime(dr_input[0]), pd.to_datetime(dr_input[1])
        else:
            start_dt = end_dt = pd.to_datetime(dr_input[0] if isinstance(dr_input, (list, tuple)) else dr_input)
        
        filtered = df[(df["Date"] >= start_dt) & (df["Date"] <= end_dt)]
    else:
        filtered = pd.DataFrame()

    st.info("Configured Floor: **$90.00**")

# -----------------------------
# 5. Main Dashboard
# -----------------------------
st.title("🏨 Econo Lodge Metro Arlington")
st.markdown('<div class="floor-price-banner">⚠️ MINIMUM RATE THRESHOLD OF $90.00 ENFORCED</div>', unsafe_allow_html=True)

if not filtered.empty:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Avg ADR", f"${filtered['ADR'].mean():.2f}")
    k2.metric("Occupancy", f"{filtered['Occupancy'].mean()*100:.1f}%")
    k3.metric("RevPAR", f"${filtered['RevPAR'].mean():.2f}")
    k4.metric("Period Revenue", f"${filtered['Room_Revenue'].sum():,.0f}")

# -----------------------------
# 6. Competitor Benchmarking
# -----------------------------
st.header("📊 Competitor Benchmarking (2026)")
comp_2026 = competitor_df.copy()
comp_2026['Month_Date'] = comp_2026['Date'].dt.to_period('M').dt.to_timestamp()
monthly_comp = comp_2026.groupby(['Month_Date', 'Hotel'])['Rate'].mean().reset_index()

fig_comp = px.line(monthly_comp, x='Month_Date', y='Rate', color='Hotel', title="Market Rate Trends")
st.plotly_chart(fig_comp, use_container_width=True)

# -----------------------------
# 7. 90-Day Predictive Pricing
# -----------------------------
st.header("📈 90-Day Forecast")
f_start = df["Date"].max() if not df.empty else datetime.today()
future_dates = pd.date_range(start=f_start + timedelta(days=1), periods=90)
forecast_df = pd.DataFrame({"Date": future_dates}).merge(events, on="Date", how="left").fillna(0)

base_adr = filtered['ADR'].mean() if not filtered.empty else 100
multipliers = {"High": 1.35, "Medium": 1.15, 0: 1.0, "None": 1.0}

def get_suggested(row):
    impact = row['Impact_Level'] if row['Impact_Level'] != 0 else 0
    rate = base_adr * multipliers.get(impact, 1.0) + row['Premium']
    return max(90.0, rate)

forecast_df["Suggested_Rate"] = forecast_df.apply(get_suggested, axis=1)

fig_f = go.Figure()
fig_f.add_trace(go.Scatter(x=forecast_df["Date"], y=forecast_df["Suggested_Rate"], name="AI Rate", line=dict(color='green', width=3)))
fig_f.add_hline(y=90, line_dash="dash", line_color="red", annotation_text="Floor")
st.plotly_chart(fig_f, use_container_width=True)

# -----------------------------
# 8. AI Query Engine
# -----------------------------
st.divider()
st.subheader("🤖 AI Pricing Engine Query")
q_date = st.date_input("Check Future Date", future_dates[0])
res = forecast_df[forecast_df["Date"] == pd.to_datetime(q_date)]
if not res.empty:
    row = res.iloc[0]
    st.metric(f"Recommended Rate for {q_date}", f"${row['Suggested_Rate']:.2f}")
    if row['Premium'] > 0: st.success(f"Event Premium Applied: {row['Event']}")
