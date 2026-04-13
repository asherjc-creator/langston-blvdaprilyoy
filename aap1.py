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
    """Loads an image and converts it to a base64 string."""
    try:
        if os.path.exists(image_path):
            img = Image.open(image_path)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    except Exception: pass
    return ""

def clean_value(val):
    """Robust cleaning for currency, percentages, and non-numeric strings."""
    if val is None or pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    val_str = str(val).replace(',', '').replace('$', '').replace('%', '').replace('"', '').strip()
    if val_str in ['∞', '', 'nan', 'None', '?', '-']: return 0.0
    try: return float(val_str)
    except ValueError: return 0.0

def get_rate_mapping(file_path):
    """Maps rate codes to categories from 'my codes.csv'."""
    if not os.path.exists(file_path): return {}
    try:
        df_raw = pd.read_csv(file_path, header=None)
        col_to_cat = {0: "Group", 1: "Wholesale", 2: "Opaque", 3: "Advance Purchase", 4: "Promotion", 28: "OTA Bundle Package", 30: "Locked/Other"}
        mapping = {}
        for col_idx, cat_name in col_to_cat.items():
            if col_idx < len(df_raw.columns):
                codes = df_raw.iloc[4:, col_idx].dropna().tolist()
                for code in codes:
                    c = str(code).strip()
                    if c and c not in ['nan', 'None', '']: mapping[c] = cat_name
        return mapping
    except Exception: return {}

def generate_competitor_data(hotel_name, base_adr, volatility=0.12):
    """Generates synthetic 2026 market data."""
    dates = pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')
    seasonal = 1 + 0.2 * np.sin(2 * np.pi * (dates.dayofyear - 90) / 365)
    weekend = np.where(dates.dayofweek >= 5, 1.15, 1.0)
    np.random.seed(abs(hash(hotel_name)) % 10000)
    rates = base_adr * seasonal * weekend * (1 + np.random.normal(0, volatility, len(dates)))
    return pd.DataFrame({'Date': dates, 'Hotel': hotel_name, 'Rate': np.maximum(rates, 65).round(2)})

# -----------------------------
# 2. Configuration & Data Load
# -----------------------------
st.set_page_config(page_title="Econo Lodge Revenue Dashboard", layout="wide", page_icon="🏨")

@st.cache_data
def load_all_data():
    rate_map = get_rate_mapping("my codes.csv")
    kpi_files = {"2023": "ECONO - 2023.csv", "2024": "ECONO - 2024.csv", "2025": "ECONO - 2025.csv", "2026": "ECONO - 2026.csv"}
    df_list = []
    
    for year, file in kpi_files.items():
        if os.path.exists(file):
            temp = pd.read_csv(file)
            temp.columns = [c.strip() for c in temp.columns]
            temp = temp.loc[:, ~temp.columns.duplicated()] # Remove duplicates
            
            # Map columns safely
            rename_map = {'IDS_DATE': 'Date', 'RoomRev': 'Room_Revenue', 'Occupied': 'Rooms_Sold', 'Rooms': 'Total_Rooms'}
            temp.rename(columns={k: v for k, v in rename_map.items() if k in temp.columns}, inplace=True)
            
            temp['Date'] = pd.to_datetime(temp['Date'], errors='coerce')
            temp = temp.dropna(subset=['Date'])
            
            for col in ['Room_Revenue', 'ADR', 'RevPAR', 'Rooms_Sold', 'Total_Rooms', 'Arrivals']:
                if col in temp.columns: temp[col] = temp[col].apply(clean_value)
            
            if 'Arrivals' not in temp.columns: temp['Arrivals'] = 0
            temp['Year'] = int(year)
            df_list.append(temp)

    full_df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
    if not full_df.empty:
        full_df['Occupancy'] = np.where(full_df['Total_Rooms'] > 0, full_df['Rooms_Sold'] / full_df['Total_Rooms'], 0.0)

    # Rate Code Analysis (with duplicate protection)
    rc_files = {"2024": "Rate code 2024.csv", "2025": "Rate code 2025.csv", "2026": "Rate code 2026.csv"}
    all_rc_list = []
    for year, path in rc_files.items():
        if os.path.exists(path):
            trc = pd.read_csv(path)
            trc.columns = [c.strip().strip('"') for c in trc.columns]
            
            # Find ID column (Rate Code)
            id_col = next((c for c in trc.columns if 'RATE' in c.upper()), trc.columns[0])
            
            # SAFE RENAMING: Only rename the FIRST match to prevent non-unique columns
            found_rev, found_nights = False, False
            rename_dict = {id_col: 'Rate_Code'}
            for col in trc.columns:
                if 'Room Revenue' in col and not found_rev:
                    rename_dict[col], found_rev = 'Room_Revenue', True
                elif ('Room Nights' in col or 'Nights' in col) and not found_nights:
                    rename_dict[col], found_nights = 'Room_Nights', True
            
            trc.rename(columns=rename_dict, inplace=True)
            trc = trc.loc[:, ~trc.columns.duplicated()] # Force uniqueness
            
            for c in ['Room_Revenue', 'Room_Nights']:
                if c in trc.columns: trc[c] = trc[c].apply(clean_value)
            
            trc['Category'] = trc['Rate_Code'].astype(str).map(rate_map).fillna('Other')
            trc['Year'] = int(year)
            all_rc_list.append(trc)
    
    all_rc = pd.concat(all_rc_list, ignore_index=True) if all_rc_list else pd.DataFrame()
    
    # Event and Competitor Setup
    events = pd.DataFrame({
        "Date": pd.to_datetime(["2026-04-12", "2026-04-13", "2026-04-14", "2026-05-15", "2026-07-04", "2026-09-20"]),
        "Event": ["Cherry Blossom Peak", "Cherry Blossom Peak", "Cherry Blossom Peak", "Tech Summit", "Independence Day", "Marine Marathon"],
        "Impact_Level": ["High", "High", "High", "Medium", "High", "Medium"],
        "Premium": [200, 200, 200, 0, 0, 0]
    })
    
    comps = {"Econo Lodge Metro Arlington": 95, "Comfort Inn Ballston": 115, "Holiday Inn Express": 125, "Days Inn": 85, "Hyatt Place": 140}
    comp_df = pd.concat([generate_competitor_data(h, r) for h, r in comps.items()], ignore_index=True)

    return full_df, all_rc, events, comp_df

df, all_rc, events, comp_df = load_all_data()

# -----------------------------
# 3. Sidebar & Layout
# -----------------------------
st.markdown("<style>.stMetric { background: white; border-radius: 10px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("Asher Jannu")
    st.caption("Revenue Analyst | Arlington Market")
    st.divider()
    if not df.empty:
        dr = st.date_input("Analysis Range", [df["Date"].min(), df["Date"].max()])
        if isinstance(dr, (list, tuple)) and len(dr) == 2:
            start, end = pd.to_datetime(dr[0]), pd.to_datetime(dr[1])
        else:
            start = end = pd.to_datetime(dr[0])
        filtered = df[(df["Date"] >= start) & (df["Date"] <= end)]
    else:
        filtered = pd.DataFrame()
    st.info("Floor Price: **$90.00**")

# -----------------------------
# 4. Dashboard Visuals
# -----------------------------
st.title("🏨 Econo Lodge Metro Arlington")
st.markdown('<div style="background:#fff3cd; padding:10px; border-radius:5px; text-align:center; color:#856404; font-weight:bold;">⚠️ AI PRICING FLOOR ENFORCED: $90.00</div>', unsafe_allow_html=True)

if not filtered.empty:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Avg ADR", f"${filtered['ADR'].mean():.2f}")
    k2.metric("Occupancy", f"{filtered['Occupancy'].mean()*100:.1f}%")
    k3.metric("RevPAR", f"${filtered['RevPAR'].mean():.2f}")
    k4.metric("Revenue", f"${filtered['Room_Revenue'].sum():,.0f}")

st.divider()
st.header("📊 2026 Market Benchmarking")
m_comp = comp_df.groupby([comp_df['Date'].dt.to_period('M').dt.to_timestamp(), 'Hotel'])['Rate'].mean().reset_index()
st.plotly_chart(px.line(m_comp, x='Date', y='Rate', color='Hotel', title="Competitor Trends"), use_container_width=True)

# -----------------------------
# 5. Predictive Pricing
# -----------------------------
st.header("📈 90-Day Predictive Pricing")
f_start = df["Date"].max() if not df.empty else datetime.today()
forecast = pd.DataFrame({"Date": pd.date_range(start=f_start + timedelta(days=1), periods=90)})
forecast = forecast.merge(events, on="Date", how="left").fillna(0)

base_adr = filtered['ADR'].mean() if not filtered.empty else 100
multipliers = {"High": 1.35, "Medium": 1.15, 0: 1.0}

def get_rate(row):
    rate = base_adr * multipliers.get(row['Impact_Level'], 1.0) + row['Premium']
    return max(90.0, rate)

forecast["Suggested_Rate"] = forecast.apply(get_rate, axis=1)

fig = go.Figure()
fig.add_trace(go.Scatter(x=forecast["Date"], y=forecast["Suggested_Rate"], name="AI Rate", line=dict(color='green', width=3)))
fig.add_hline(y=90, line_dash="dash", line_color="red", annotation_text="Floor")
st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 6. AI Query Engine
# -----------------------------
st.subheader("🤖 AI Rate Query")
q_date = st.date_input("Check Future Date", forecast["Date"].iloc[0])
res = forecast[forecast["Date"] == pd.to_datetime(q_date)]
if not res.empty:
    r = res.iloc[0]
    st.metric(f"Rate for {q_date}", f"${r['Suggested_Rate']:.2f}")
    if r['Premium'] > 0: st.success(f"Event: {r['Event']}")
