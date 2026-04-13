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
    if val is None:
        return 0.0
    try:
        if isinstance(val, (pd.Series, pd.DataFrame)):
            return val
        if pd.isna(val):
            return 0.0
    except:
        pass
    val_str = str(val).replace(',', '').replace('$', '').replace('%', '').replace('"', '').strip()
    if val_str in ['∞', '', 'nan', 'None', '?']:
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
            0: "Group", 
            1: "Wholesale", 
            2: "Opaque", 
            3: "Advance Purchase", 
            4: "Promotion", 
            28: "OTA Bundle Package", 
            30: "Locked/Other"
        }
        
        mapping = {}
        for col_idx, cat_name in col_to_cat.items():
            if col_idx < len(df_raw.columns):
                codes = df_raw.iloc[4:, col_idx].dropna().tolist()
                for code in codes:
                    code_clean = str(code).strip()
                    if code_clean:
                        mapping[code_clean] = cat_name
        return mapping
    except Exception as e:
        st.warning(f"Could not load rate mapping: {e}")
        return {}

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
.category-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 3. Data Loading & Cleaning
# -----------------------------
@st.cache_data
def load_all_data():
    # Load Rate Code Mapping
    rate_mapping = get_rate_mapping("my codes.csv")
    
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
            temp.columns = [c.strip() for c in temp.columns]
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
                    temp[col] = temp[col].apply(clean_value)
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

    # B. Load Rate Code Files with Category Mapping
    rc_files = {
        "2024": "Rate code 2024.csv",
        "2025": "Rate code 2025.csv",
        "2026": "Rate code 2026.csv"
    }
    rc_data = {}
    all_rc_list = []
    
    for year, path in rc_files.items():
        if os.path.exists(path):
            temp_rc = pd.read_csv(path)
            temp_rc.columns = [c.strip().strip('"') for c in temp_rc.columns]
            
            # Identify the ID column
            id_col = None
            for col in temp_rc.columns:
                if col.upper() in ['RATE CODE', 'IDS_RATE_CODE', 'RATE_CODE']:
                    id_col = col
                    break
            if id_col is None:
                id_col = temp_rc.columns[0]
            
            # Clean numeric columns
            for col in temp_rc.columns:
                if col != id_col:
                    temp_rc[col] = temp_rc[col].apply(clean_value)
            
            # Add category
            temp_rc['Category'] = temp_rc[id_col].map(rate_mapping).fillna('Other/Uncategorized')
            temp_rc['Year'] = int(year)
            
            # Standardize column names
            temp_rc.rename(columns={
                id_col: 'Rate_Code',
                'Room Revenue': 'Room_Revenue',
                'Room Nights': 'Room_Nights'
            }, inplace=True)
            
            rc_data[year] = temp_rc
            all_rc_list.append(temp_rc)
    
    all_rc = pd.concat(all_rc_list, ignore_index=True) if all_rc_list else pd.DataFrame()

    # C. Generate Yearly Summary
    yearly_summary = pd.DataFrame()
    if not full_df.empty:
        yearly_summary = full_df.groupby('Year').agg({
            'Room_Revenue': 'sum',
            'Rooms_Sold': 'sum',
            'Total_Rooms': 'sum'
        }).reset_index()
        yearly_summary['Occupancy%'] = (yearly_summary['Rooms_Sold'] / yearly_summary['Total_Rooms'] * 100).round(2)
        yearly_summary['ADR'] = (yearly_summary['Room_Revenue'] / yearly_summary['Rooms_Sold']).round(2)
        yearly_summary['RevPAR'] = (yearly_summary['Room_Revenue'] / yearly_summary['Total_Rooms']).round(2)

    # D. Category Summary
    cat_summary = pd.DataFrame()
    if not all_rc.empty:
        cat_summary = all_rc.groupby(['Year', 'Category']).agg({
            'Room_Revenue': 'sum',
            'Room_Nights': 'sum'
        }).reset_index()
        cat_summary = cat_summary.sort_values(['Year', 'Room_Revenue'], ascending=[True, False])

    # E. Events with Premium Dates
    events = pd.DataFrame({
        "Date": pd.to_datetime([
            "2026-04-12", "2026-04-13", "2026-04-14",
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
        "Premium": [200, 200, 200, 0, 0, 0]
    })

    return full_df, rc_data, all_rc, yearly_summary, cat_summary, rate_mapping, events

df, rc_dict, all_rc, yearly_summary, cat_summary, rate_mapping, events = load_all_data()

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
    
    # Show mapping stats
    if rate_mapping:
        st.markdown("---")
        st.caption(f"✅ Rate mapping loaded: {len(rate_mapping)} codes categorized")

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
# 6. Yearly Performance Summary KPI Row
# -----------------------------
st.write("### 📊 Yearly Performance Summary")
if not yearly_summary.empty:
    # Display as metrics
    cols = st.columns(len(yearly_summary))
    for i, (_, row) in enumerate(yearly_summary.iterrows()):
        with cols[i]:
            st.metric(
                f"{int(row['Year'])}",
                f"${row['Room_Revenue']:,.0f}",
                delta=f"{row['Occupancy%']:.1f}% Occ | ${row['ADR']:.0f} ADR"
            )

# Current period KPIs
if not filtered.empty:
    st.write("### 📈 Selected Period KPIs")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Average ADR", f"${filtered['ADR'].mean():.2f}")
    k2.metric("Occupancy", f"{filtered['Occupancy'].mean()*100:.1f}%")
    k3.metric("RevPAR", f"${filtered['RevPAR'].mean():.2f}")
    k4.metric("Total Revenue", f"${filtered['Room_Revenue'].sum():,.0f}")

# -----------------------------
# 7. Rate Category Analysis (New Section)
# -----------------------------
st.divider()
st.header("📂 Rate Category Performance Analysis")

if not cat_summary.empty:
    # Category trend over years
    cat_pivot = cat_summary.pivot_table(
        index='Category', 
        columns='Year', 
        values='Room_Revenue', 
        aggfunc='sum',
        fill_value=0
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Stacked bar chart for category contribution
        fig_cat = px.bar(
            cat_summary, 
            x='Year', 
            y='Room_Revenue', 
            color='Category',
            title="Revenue by Rate Category (2024-2026)",
            labels={'Room_Revenue': 'Revenue ($)'},
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_cat.update_layout(height=400)
        st.plotly_chart(fig_cat, use_container_width=True)
    
    with col2:
        st.subheader("2026 Category Mix")
        cat_2026 = cat_summary[cat_summary['Year'] == 2026].nlargest(5, 'Room_Revenue')
        for _, row in cat_2026.iterrows():
            st.metric(
                row['Category'], 
                f"${row['Room_Revenue']:,.0f}",
                delta=f"{row['Room_Nights']:.0f} nights"
            )
    
    # Category performance table
    st.subheader("📋 Detailed Category Breakdown")
    cat_display = cat_summary.pivot_table(
        index=['Year', 'Category'], 
        values=['Room_Revenue', 'Room_Nights'],
        aggfunc='sum'
    ).reset_index()
    cat_display = cat_display.sort_values(['Year', 'Room_Revenue'], ascending=[True, False])
    cat_display['Room_Revenue'] = cat_display['Room_Revenue'].apply(lambda x: f"${x:,.0f}")
    cat_display['Room_Nights'] = cat_display['Room_Nights'].apply(lambda x: f"{x:,.0f}")
    st.dataframe(cat_display, hide_index=True, use_container_width=True)

# -----------------------------
# 8. 2025 Gap Analysis: ADR vs RevPAR
# -----------------------------
st.divider()
st.header("🔍 2025 Gap Analysis: ADR vs RevPAR")
df25 = df[df['Date'].dt.year == 2025].sort_values('Date')

if not df25.empty:
    df25['Month'] = df25['Date'].dt.to_period('M')
    monthly_avg = df25.groupby('Month').agg({
        'ADR': 'mean',
        'RevPAR': 'mean',
        'Occupancy': 'mean',
        'Room_Revenue': 'sum'
    }).reset_index()
    monthly_avg['Month_Date'] = monthly_avg['Month'].dt.to_timestamp()

    fig_gap = go.Figure()
    
    fig_gap.add_trace(go.Scatter(
        x=df25['Date'], y=df25['ADR'],
        name='ADR (Daily)', line=dict(color='#2ca02c', width=1), opacity=0.4
    ))
    fig_gap.add_trace(go.Scatter(
        x=df25['Date'], y=df25['RevPAR'],
        name='RevPAR (Daily)', line=dict(color='#d62728', width=1, dash='dot'), opacity=0.4
    ))
    
    fig_gap.add_trace(go.Scatter(
        x=monthly_avg['Month_Date'], y=monthly_avg['ADR'],
        name='ADR (Monthly Avg)', line=dict(color='#2ca02c', width=3)
    ))
    fig_gap.add_trace(go.Scatter(
        x=monthly_avg['Month_Date'], y=monthly_avg['RevPAR'],
        name='RevPAR (Monthly Avg)', line=dict(color='#d62728', width=3, dash='dot')
    ))
    
    fig_gap.add_trace(go.Scatter(
        x=df25['Date'], y=df25['ADR'] - df25['RevPAR'],
        fill='tozeroy',
        name='Gap (ADR - RevPAR)',
        line=dict(color='rgba(0,0,0,0)'),
        fillcolor='rgba(255,165,0,0.2)'
    ))
    
    fig_gap.update_layout(
        title="2025 ADR, RevPAR, and the Gap Between Them",
        yaxis_title="USD",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_gap, use_container_width=True)

    avg_adr_25 = df25['ADR'].mean()
    avg_revpar_25 = df25['RevPAR'].mean()
    avg_occ_25 = df25['Occupancy'].mean() * 100
    gap_25 = avg_adr_25 - avg_revpar_25
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avg ADR 2025", f"${avg_adr_25:.2f}")
    m2.metric("Avg RevPAR 2025", f"${avg_revpar_25:.2f}")
    m3.metric("Avg Occupancy 2025", f"{avg_occ_25:.1f}%")
    m4.metric("ADR-RevPAR Gap", f"${gap_25:.2f}")

    st.markdown(f"""
    ---
    ### 📋 2025 Gap Analysis Observations
    
    **Key Finding**: The average ADR-RevPAR gap in 2025 was **${gap_25:.2f}**, driven by an average occupancy of **{avg_occ_25:.1f}%**.
    
    **Observation**: The gap between ADR and RevPAR in 2025 indicates that while ADR remained relatively stable, occupancy was not consistently high enough to maximize RevPAR.
    
    **Recommendations for 2026**:
    1. **Push Weekend Rates**: With Cherry Blossom and peak tourism dates, implement +$200 premium pricing.
    2. **Rebuild Corporate Base**: Target local government contractors and tech firms.
    3. **Group Business Development**: Actively solicit small corporate groups and sports teams.
    4. **Length-of-Stay Restrictions**: Implement minimum stays on high-demand weekends.
    """)

else:
    st.warning("No 2025 data available for gap analysis.")

# -----------------------------
# 9. Rate Code Analysis - Top Performers
# -----------------------------
st.divider()
st.header("🔑 Top Performing Rate Codes by Year")
rc1, rc2, rc3 = st.columns(3)

for i, year in enumerate([2024, 2025, 2026]):
    with [rc1, rc2, rc3][i]:
        st.subheader(f"Top Codes {year}")
        if str(year) in rc_dict and not rc_dict[str(year)].empty:
            rc_year = rc_dict[str(year)].copy()
            if 'Room_Revenue' in rc_year.columns and 'Rate_Code' in rc_year.columns:
                top_codes = rc_year.nlargest(5, 'Room_Revenue')[['Rate_Code', 'Room_Revenue', 'Category']]
                top_codes['Room_Revenue'] = top_codes['Room_Revenue'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(top_codes, hide_index=True)
            else:
                st.write("Data format issue")
        else:
            st.write(f"No {year} rate code data.")

st.caption("Note: Rate code files contain aggregated yearly data with category mapping applied.")

# -----------------------------
# 10. 2026 Reservation Activity Analysis
# -----------------------------
st.divider()
st.header("📊 2026 Reservation Activity Analysis")

df26 = df[df['Date'].dt.year == 2026].sort_values('Date')
if not df26.empty:
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

    df25_comp = df[df['Date'].dt.year == 2025].sort_values('Date')
    if not df25_comp.empty:
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

        total_arr_26 = df26['Arrivals'].sum()
        total_arr_25 = df25_comp[df25_comp['DayOfYear'] <= df26['DayOfYear'].max()]['Arrivals'].sum()
        st.metric("Total Arrivals YTD 2026", f"{total_arr_26:.0f}",
                  delta=f"{total_arr_26 - total_arr_25:.0f} vs 2025 same period")
else:
    st.warning("No 2026 reservation data available.")

# -----------------------------
# 11. 90-Day Predictive Pricing
# -----------------------------
st.divider()
st.header("📈 90-Day Forecast & Predictive Pricing")

if not filtered.empty:
    forecast_start = filtered["Date"].max()
else:
    forecast_start = df["Date"].max() if not df.empty else datetime.today()

future_dates = pd.date_range(start=forecast_start + timedelta(days=1), periods=90)
forecast_df = pd.DataFrame({"Date": future_dates})
forecast_df = forecast_df.merge(events, on="Date", how="left").fillna({"Impact_Level": "None", "Event": "Standard Market", "Premium": 0})

base_adr = filtered['ADR'].mean() if not filtered.empty else df["ADR"].mean()
multipliers = {"High": 1.30, "Medium": 1.15, "None": 1.0}
np.random.seed(42)

def calculate_rate(row):
    rate = base_adr * multipliers[row["Impact_Level"]] * np.random.uniform(0.95, 1.05)
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

# -----------------------------
# 14. Export Section
# -----------------------------
st.divider()
st.header("📥 Export Analysis Data")

col_exp1, col_exp2, col_exp3 = st.columns(3)

with col_exp1:
    if not yearly_summary.empty:
        csv_yearly = yearly_summary.to_csv(index=False)
        st.download_button(
            label="📊 Download Yearly Summary",
            data=csv_yearly,
            file_name="yearly_performance_summary.csv",
            mime="text/csv"
        )

with col_exp2:
    if not cat_summary.empty:
        csv_cat = cat_summary.to_csv(index=False)
        st.download_button(
            label="📂 Download Category Summary",
            data=csv_cat,
            file_name="rate_category_summary.csv",
            mime="text/csv"
        )

with col_exp3:
    if not all_rc.empty:
        csv_rc = all_rc.to_csv(index=False)
        st.download_button(
            label="🔑 Download All Rate Codes",
            data=csv_rc,
            file_name="all_rate_codes_with_categories.csv",
            mime="text/csv"
        )
