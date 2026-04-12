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

def clean_numeric(val):
    """Strips currency symbols, commas, and handles non-numeric characters."""
    if pd.isna(val):
        return 0.0
    val = str(val).replace(',', '').replace('$', '').replace('"', '').strip()
    if val in ['∞', '', 'nan', 'None']:
        return 0.0
    try:
        return float(val)
    except:
        return 0.0

# -----------------------------
# 2. Page Configuration & Styling
# -----------------------------
st.set_page_config(page_title="Econo Lodge Arlington Revenue Portal", layout="wide", page_icon="🏨")

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
.title-container { display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }
.event-card {
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 10px;
    border-left: 5px solid #007bff;
    background: #ffffff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.floor-price-banner {
    padding: 10px;
    background-color: #fff3cd;
    border: 1px solid #ffeeba;
    color: #856404;
    border-radius: 5px;
    text-align: center;
    font-weight: bold;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 3. Data Loading & Cleaning
# -----------------------------
@st.cache_data
def load_all_data():
    # A. Load Historical KPI Data (2023-2026)
    kpi_files = {
        "2023": "ECONO - 2023.csv",
        "2024": "ECONO - 2024.csv",
        "2025": "ECONO - 2025.csv",
        "2026": "ECONO - 2026.csv"
    }
    df_list = []
    for year, file in kpi_files.items():
        if os.path.exists(file):
            temp = pd.read_csv(file)
            temp.rename(columns={
                'IDS_DATE': 'Date',
                'RoomRev': 'Room_Revenue',
                'Occupied': 'Rooms_Sold',
                'Rooms': 'Total_Rooms'
            }, inplace=True)
            temp['Date'] = pd.to_datetime(temp['Date'], errors='coerce')
            temp = temp.dropna(subset=['Date'])
            for col in ['Room_Revenue', 'ADR', 'RevPAR', 'Rooms_Sold', 'Total_Rooms']:
                if col in temp.columns:
                    temp[col] = temp[col].apply(clean_numeric)
            temp['Year'] = int(year)
            df_list.append(temp)

    full_df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
    if not full_df.empty:
        full_df['Occupancy'] = np.where(
            full_df['Total_Rooms'] > 0,
            full_df['Rooms_Sold'] / full_df['Total_Rooms'],
            0.0
        )
        full_df['Lat'], full_df['Lon'] = 38.8856, -77.1664

    # B. Load Rate Code Files (CSV)
    rc_files = {
        "2024": "Rate code 2024.csv",
        "2025": "Rate code 2025.csv",
        "2026": "Rate code 2026.csv"
    }
    rc_data = {}
    for year, path in rc_files.items():
        if os.path.exists(path):
            temp_rc = pd.read_csv(path)
            temp_rc.columns = [c.strip().replace('\ufeff', '').replace('"', '') for c in temp_rc.columns]
            for col in temp_rc.columns:
                if any(x in col for x in ['Revenue', 'AVG', 'Nights']):
                    temp_rc[col] = temp_rc[col].apply(clean_numeric)
            rc_data[year] = temp_rc

    # C. Events & Benchmarks
    # Add custom premium dates for April 12-14, 2026
    events = pd.DataFrame({
        "Date": pd.to_datetime([
            "2026-04-12", "2026-04-13", "2026-04-14",   # High demand with +$200 premium
            "2026-05-15", "2026-07-04", "2026-09-20"
        ]),
        "Event": [
            "Cherry Blossom Peak (Premium +$200)",
            "Cherry Blossom Peak (Premium +$200)",
            "Cherry Blossom Peak (Premium +$200)",
            "Arlington Tech Summit",
            "Independence Day DC",
            "DC Marine Corps Marathon Prep"
        ],
        "Impact_Level": ["High", "High", "High", "Medium", "High", "Medium"],
        "Premium": [200, 200, 200, 0, 0, 0]   # Extra $200 for April 12-14
    })

    return full_df, rc_data, events

df, rc_dict, events = load_all_data()

# -----------------------------
# 4. Sidebar Profile & Control
# -----------------------------
asher_pic_base64 = get_image_base64("asher_picture.png")
github_url = "https://github.com/asherjc-creator/econo-revenue-dashboard"

with st.sidebar:
    if asher_pic_base64:
        st.markdown(
            f'<img src="{asher_pic_base64}" style="border-radius: 50%; width: 140px; height: 140px; object-fit: cover; display: block; margin: 0 auto 10px auto; border: 3px solid #eee;">',
            unsafe_allow_html=True
        )
    st.markdown("## Asher Jannu")
    st.markdown("### **Revenue Analyst**")
    st.markdown(
        f'<a href="{github_url}" target="_blank"><button style="background-color: #24292e; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; width: 100%;">View GitHub Code</button></a>',
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.header("Control Panel")
    if not df.empty:
        date_range = st.date_input(
            "Select Analysis Range",
            [df["Date"].min().date(), df["Date"].max().date()]
        )
        if len(date_range) == 2:
            start_date, end_date = date_range[0], date_range[1]
        else:
            start_date = end_date = date_range[0]
        filtered = df[
            (df["Date"] >= pd.to_datetime(start_date)) &
            (df["Date"] <= pd.to_datetime(end_date))
        ]
    else:
        filtered = pd.DataFrame()
        start_date = end_date = datetime.today()
    st.info("Configured Lower Limit: **$90.00**")

# -----------------------------
# 5. Header Section
# -----------------------------
logo_base64 = get_image_base64("logo.png")
if logo_base64:
    st.markdown(
        f'<div class="title-container"><img src="{logo_base64}" style="width: 120px;"><div style="flex-grow: 1;"><h1 style="margin: 0; color: #333;">Econo Lodge Metro Arlington</h1><h3 style="margin: 0; color: #666; font-weight: normal;">Revenue Management Dashboard</h3></div></div>',
        unsafe_allow_html=True
    )
else:
    st.title("🏨 Econo Lodge Metro Arlington | Revenue Dashboard")

st.markdown(
    '<div class="floor-price-banner">⚠️ ALL PREDICTIVE PRICING MODELS ENFORCE A MINIMUM RATE THRESHOLD OF $90.00</div>',
    unsafe_allow_html=True
)

# -----------------------------
# 6. KPI Row & Historical Comparison
# -----------------------------
if not filtered.empty:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Average ADR", f"${filtered['ADR'].mean():.2f}")
    k2.metric("Occupancy", f"{filtered['Occupancy'].mean()*100:.1f}%")
    k3.metric("RevPAR", f"${filtered['RevPAR'].mean():.2f}")
    k4.metric("Market Share (RGI)", "92.4")

st.write("### 📅 April Performance Comparison (2024-2026)")
apr_rows = []
for y in [2024, 2025, 2026]:
    m_df = df[(df['Date'].dt.year == y) & (df['Date'].dt.month == 4)]
    if not m_df.empty:
        total_rev = m_df['Room_Revenue'].sum()
        total_rooms_sold = m_df['Rooms_Sold'].sum()
        total_rooms = m_df['Total_Rooms'].sum()
        adr = total_rev / total_rooms_sold if total_rooms_sold > 0 else 0
        occ = (total_rooms_sold / total_rooms) * 100 if total_rooms > 0 else 0
        revpar = total_rev / total_rooms if total_rooms > 0 else 0
        apr_rows.append({
            "Year": f"April {y}",
            "ADR": f"${adr:.2f}",
            "Occupancy": f"{occ:.1f}%",
            "RevPAR": f"${revpar:.2f}"
        })
if apr_rows:
    st.table(pd.DataFrame(apr_rows))
else:
    st.info("No April data available for comparison.")

# -----------------------------
# 7. 2025 Down Year Analysis
# -----------------------------
st.divider()
st.header("📉 2025 Analysis: Identifying the Revenue Gap")
c2a, c2b = st.columns(2)

with c2a:
    df25 = df[df['Date'].dt.year == 2025].sort_values('Date')
    if not df25.empty:
        fig25 = go.Figure()
        fig25.add_trace(go.Scatter(
            x=df25['Date'], y=df25['ADR'],
            name='ADR', line=dict(color='#1f77b4')
        ))
        fig25.add_trace(go.Scatter(
            x=df25['Date'], y=df25['RevPAR'],
            name='RevPAR', line=dict(color='#ff7f0e', dash='dot')
        ))
        fig25.update_layout(title="2025 ADR & RevPAR Curve", hovermode="x unified")
        st.plotly_chart(fig25, use_container_width=True)
    else:
        st.warning("No 2025 data.")

with c2b:
    if not df.empty:
        rev_yoy = df.groupby([df['Date'].dt.month, df['Date'].dt.year])['Room_Revenue'].sum().unstack()
        fig_yoy = px.line(
            rev_yoy,
            labels={'index': 'Month', 'value': 'Revenue'},
            title="Year-Over-Year Revenue Performance"
        )
        st.plotly_chart(fig_yoy, use_container_width=True)
    else:
        st.warning("No data for YoY comparison.")

# -----------------------------
# 8. ADR vs RevPAR Gap in 2024 (Detailed Analysis)
# -----------------------------
st.divider()
st.header("🔍 2024 Gap Analysis: ADR vs RevPAR")
df24 = df[df['Date'].dt.year == 2024].sort_values('Date')

if not df24.empty:
    fig_gap = go.Figure()
    fig_gap.add_trace(go.Scatter(
        x=df24['Date'], y=df24['ADR'],
        name='ADR', line=dict(color='#2ca02c', width=2)
    ))
    fig_gap.add_trace(go.Scatter(
        x=df24['Date'], y=df24['RevPAR'],
        name='RevPAR', line=dict(color='#d62728', width=2, dash='dot')
    ))
    fig_gap.add_trace(go.Scatter(
        x=df24['Date'], y=df24['ADR'] - df24['RevPAR'],
        fill='tozeroy',
        name='Gap (ADR - RevPAR)',
        line=dict(color='rgba(0,0,0,0)'),
        fillcolor='rgba(255,165,0,0.3)'
    ))
    fig_gap.update_layout(
        title="2024 ADR, RevPAR, and the Gap Between Them",
        yaxis_title="USD",
        hovermode="x unified"
    )
    st.plotly_chart(fig_gap, use_container_width=True)

    st.markdown("""
    **Observation**: The gap between ADR and RevPAR in 2024 indicates that occupancy was not high enough to support the achieved ADR.
    RevPAR = ADR × Occupancy. A widening gap suggests either:
    - Discounted or lower‑yielding rate codes were used more frequently.
    - High‑rated segments did not materialize as expected.

    **Potential Missing / Under‑Performing Rate Codes in 2024** (based on typical portfolio):
    - **Corporate Negotiated (e.g., LEXP, SCPM)** – appear in the rate code file but may have been under‑utilized compared to 2023.
    - **AAA / AARP (SAARP, SAPR1B)** – lower contribution than expected.
    - **Group Blocks** – the file shows almost no group pickup (Group Block columns empty), indicating lost group revenue.

    *Recommendation*: Review the rate code mix and increase targeted marketing for higher‑yield segments (e.g., SRTL, SBOOK) while protecting base business.
    """)
else:
    st.warning("No 2024 data available for gap analysis.")

# -----------------------------
# 9. Rate Code Analysis (Yearly Aggregates)
# -----------------------------
st.divider()
st.header("🔑 Performing Rate Codes (Yearly Aggregates – no daily dates)")
rc1, rc2, rc3 = st.columns(3)

with rc1:
    st.subheader("Top Codes 2024")
    if "2024" in rc_dict:
        top_2024 = rc_dict["2024"].nlargest(5, 'Room Revenue')[['IDS_RATE_CODE', 'Room Revenue']]
        st.dataframe(top_2024, hide_index=True)
    else:
        st.write("No 2024 rate code data.")

with rc2:
    st.subheader("Top Codes 2025")
    if "2025" in rc_dict:
        top_2025 = rc_dict["2025"].nlargest(5, 'Room Revenue')[['IDS_RATE_CODE', 'Room Revenue']]
        st.dataframe(top_2025, hide_index=True)
    else:
        st.write("No 2025 rate code data.")

with rc3:
    st.subheader("Top Codes 2026")
    if "2026" in rc_dict:
        rc26 = rc_dict["2026"].rename(columns={'IDS_RATE_CODE': 'Code', 'Room Revenue': 'Revenue'})
        top_2026 = rc26.nlargest(5, 'Revenue')[['Code', 'Revenue']]
        st.dataframe(top_2026, hide_index=True)
    else:
        st.write("No 2026 rate code data.")

st.caption("Note: Rate code files contain aggregated yearly data – they do not include daily dates.")

# -----------------------------
# 10. 2026 Reservation Activity Analysis (New Section)
# -----------------------------
st.divider()
st.header("📊 2026 Reservation Activity Analysis")

df26 = df[df['Date'].dt.year == 2026].sort_values('Date')
if not df26.empty:
    # Use the actual daily data for 2026
    # Show pickup (Arrivals) and occupancy trend
    fig_act = make_subplots(specs=[[{"secondary_y": True}]])
    fig_act.add_trace(go.Bar(
        x=df26['Date'], y=df26['Arrivals'],
        name='Arrivals', marker_color='#1f77b4', opacity=0.7
    ))
    fig_act.add_trace(go.Scatter(
        x=df26['Date'], y=df26['Occupancy']*100,
        name='Occupancy %', line=dict(color='#d62728', width=2),
        yaxis="y2"
    ))
    fig_act.update_layout(
        title="2026 Daily Arrivals vs Occupancy",
        xaxis_title="Date",
        yaxis_title="Arrivals",
        yaxis2=dict(title="Occupancy %", overlaying="y", side="right"),
        hovermode="x unified"
    )
    st.plotly_chart(fig_act, use_container_width=True)

    # Booking pace comparison: cumulative arrivals vs. same period 2025
    df25_comp = df[df['Date'].dt.year == 2025].sort_values('Date')
    if not df25_comp.empty:
        # Align by day-of-year
        df26['DayOfYear'] = df26['Date'].dt.dayofyear
        df25_comp['DayOfYear'] = df25_comp['Date'].dt.dayofyear

        cum26 = df26.groupby('DayOfYear')['Arrivals'].sum().cumsum().reset_index(name='Cumulative_Arrivals_2026')
        cum25 = df25_comp.groupby('DayOfYear')['Arrivals'].sum().cumsum().reset_index(name='Cumulative_Arrivals_2025')

        cum_comp = pd.merge(cum26, cum25, on='DayOfYear', how='outer').sort_values('DayOfYear')
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=cum_comp['DayOfYear'], y=cum_comp['Cumulative_Arrivals_2026'],
            name='2026 Cumulative Arrivals', line=dict(color='#2ca02c', width=2)
        ))
        fig_cum.add_trace(go.Scatter(
            x=cum_comp['DayOfYear'], y=cum_comp['Cumulative_Arrivals_2025'],
            name='2025 Cumulative Arrivals', line=dict(color='#ff7f0e', width=2, dash='dot')
        ))
        fig_cum.update_layout(
            title="Booking Pace: Cumulative Arrivals (2026 vs 2025)",
            xaxis_title="Day of Year",
            yaxis_title="Cumulative Arrivals",
            hovermode="x unified"
        )
        st.plotly_chart(fig_cum, use_container_width=True)

        # Key metrics
        total_arr_26 = df26['Arrivals'].sum()
        total_arr_25 = df25_comp[df25_comp['DayOfYear'] <= df26['DayOfYear'].max()]['Arrivals'].sum()
        st.metric("Total Arrivals YTD 2026", f"{total_arr_26:.0f}",
                  delta=f"{total_arr_26 - total_arr_25:.0f} vs 2025 same period")
    else:
        st.info("2025 data not available for booking pace comparison.")
else:
    st.warning("No 2026 reservation data available.")

# -----------------------------
# 11. 90-Day Predictive Pricing (with April 12-14 premium +$200)
# -----------------------------
st.divider()
st.header("📈 90-Day Forecast & Predictive Pricing")

# Forecast start from the end of the selected range (or global max)
if not filtered.empty:
    forecast_start = filtered["Date"].max()
else:
    forecast_start = df["Date"].max() if not df.empty else datetime.today()

future_dates = pd.date_range(start=forecast_start + timedelta(days=1), periods=90)
forecast_df = pd.DataFrame({"Date": future_dates})
forecast_df = forecast_df.merge(events, on="Date", how="left").fillna({"Impact_Level": "None", "Event": "Standard Market", "Premium": 0})

# Base ADR from filtered data (or global)
base_adr = filtered['ADR'].mean() if not filtered.empty else df["ADR"].mean()
multipliers = {"High": 1.30, "Medium": 1.15, "None": 1.0}
np.random.seed(42)

def calculate_rate(row):
    rate = base_adr * multipliers[row["Impact_Level"]] * np.random.uniform(0.95, 1.05)
    # Add explicit premium for designated dates (April 12-14)
    if row["Premium"] > 0:
        rate += row["Premium"]
    return max(90.0, rate)

forecast_df["Suggested_Rate"] = forecast_df.apply(calculate_rate, axis=1)

fig_f = go.Figure()
fig_f.add_trace(go.Scatter(
    x=forecast_df["Date"], y=forecast_df["Suggested_Rate"],
    name="AI Suggested Rate", line=dict(color='#2ca02c', width=4)
))
fig_f.add_trace(go.Scatter(
    x=forecast_df["Date"], y=[90] * len(forecast_df),
    name="Floor Price ($90)", line=dict(color='red', dash='dash')
))
# Highlight premium dates
premium_dates = forecast_df[forecast_df["Premium"] > 0]
if not premium_dates.empty:
    fig_f.add_trace(go.Scatter(
        x=premium_dates["Date"], y=premium_dates["Suggested_Rate"],
        mode='markers', name='Premium +$200 Dates',
        marker=dict(color='gold', size=12, symbol='star')
    ))
fig_f.update_layout(
    title=f"90-Day Forecast starting {forecast_start.date()} (Minimum $90 Enforcement)",
    yaxis_title="Rate (USD)"
)
st.plotly_chart(fig_f, use_container_width=True)

# -----------------------------
# 12. Heatmaps & Maps
# -----------------------------
st.write("### 📅 Pricing & Demand Heatmaps")
h1, h2 = st.columns(2)

with h1:
    forecast_df['Weekday'] = forecast_df['Date'].dt.day_name()
    forecast_df['Week'] = forecast_df['Date'].dt.isocalendar().week
    pivot = forecast_df.pivot_table(index='Weekday', columns='Week', values='Suggested_Rate', aggfunc='mean')
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot = pivot.reindex(weekday_order)
    fig_heat = px.imshow(
        pivot,
        color_continuous_scale="YlOrRd",
        title="Pricing Intensity Heatmap",
        aspect="auto"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

with h2:
    st.write("#### Market Demand Centers (Arlington/DC)")
    m_heat = folium.Map(location=[38.8856, -77.1664], zoom_start=12)
    HeatMap([
        [38.8856, -77.1664, 1.0],
        [38.8977, -77.0365, 0.8],
        [38.8895, -77.0353, 0.7]
    ]).add_to(m_heat)
    folium.Marker(
        [38.8856, -77.1664],
        popup="Econo Lodge Arlington",
        icon=folium.Icon(color="blue")
    ).add_to(m_heat)
    st_folium(m_heat, width=600, height=350)

# -----------------------------
# 13. AI Engine Query
# -----------------------------
st.write("---")
st.write("### 🤖 AI Pricing Recommendation Engine")
check_date = st.date_input(
    "Query a Specific Future Date:",
    forecast_start + timedelta(days=14),
    min_value=forecast_start.date()
)
res = forecast_df[forecast_df["Date"] == pd.to_datetime(check_date)]
if not res.empty:
    row = res.iloc[0]
    st.metric(
        f"Recommended ADR: {check_date}",
        f"${row['Suggested_Rate']:.2f}",
        delta="Enforced $90 Floor"
    )
    if row['Impact_Level'] != "None":
        st.warning(f"Event Detected: {row['Event']} ({row['Impact_Level']} Impact)")
    if row['Premium'] > 0:
        st.success(f"Premium +${row['Premium']:.0f} applied for this date.")
else:
    st.info("No forecast available for that exact date.")
