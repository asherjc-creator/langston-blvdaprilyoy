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
    """Maps rate codes to their respective categories from my codes.csv."""
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
                    if code_clean and code_clean not in ['nan', 'None', '']:
                        mapping[code_clean] = cat_name
        return mapping
    except Exception as e:
        st.warning(f"Could not load rate mapping: {e}")
        return {}

def generate_competitor_data(hotel_name, base_adr, volatility=0.15):
    """Generate synthetic competitor rate data for 2026."""
    dates = pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')
    
    seasonal = 1 + 0.2 * np.sin(2 * np.pi * (dates.dayofyear - 90) / 365)
    weekend_premium = np.where(dates.dayofweek >= 5, 1.15, 1.0)
    
    np.random.seed(hash(hotel_name) % 10000)
    random_walk = 1 + np.cumsum(np.random.normal(0, volatility/30, len(dates)))
    random_walk = random_walk / random_walk[0]
    
    rates = base_adr * seasonal * weekend_premium * random_walk
    rates = np.maximum(rates, 65)
    
    return pd.DataFrame({
        'Date': dates,
        'Hotel': hotel_name,
        'Rate': rates.round(2)
    })

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
.competitor-card {
    background: white;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 10px;
    border: 1px solid #e0e0e0;
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
    rate_mapping = get_rate_mapping("my codes.csv")
    
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
            
            id_col = None
            for col in temp_rc.columns:
                if col.upper() in ['RATE CODE', 'IDS_RATE_CODE', 'RATE_CODE']:
                    id_col = col
                    break
            if id_col is None:
                id_col = temp_rc.columns[0]
            
            for col in temp_rc.columns:
                if col != id_col:
                    temp_rc[col] = temp_rc[col].apply(clean_value)
            
            temp_rc['Category'] = temp_rc[id_col].map(rate_mapping).fillna('Other/Uncategorized')
            temp_rc['Year'] = int(year)
            
            rename_dict = {id_col: 'Rate_Code'}
            for col in temp_rc.columns:
                if 'Room Revenue' in col:
                    rename_dict[col] = 'Room_Revenue'
                elif 'Room Nights' in col:
                    rename_dict[col] = 'Room_Nights'
            temp_rc.rename(columns=rename_dict, inplace=True)
            
            rc_data[year] = temp_rc
            all_rc_list.append(temp_rc)
    
    all_rc = pd.concat(all_rc_list, ignore_index=True) if all_rc_list else pd.DataFrame()

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

    cat_summary = pd.DataFrame()
    if not all_rc.empty:
        if 'Room_Revenue' in all_rc.columns and 'Room_Nights' in all_rc.columns:
            cat_summary = all_rc.groupby(['Year', 'Category']).agg({
                'Room_Revenue': 'sum',
                'Room_Nights': 'sum'
            }).reset_index()
            cat_summary = cat_summary.sort_values(['Year', 'Room_Revenue'], ascending=[True, False])

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

    competitors = {
        "Econo Lodge Metro Arlington": 95,
        "Comfort Inn Ballston": 115,
        "Holiday Inn Express Arlington": 125,
        "Days Inn by Wyndham Arlington": 85,
        "Red Lion Hotel Rosslyn": 105,
        "Hyatt Place Arlington": 140,
        "Hilton Garden Inn Arlington": 150
    }
    
    comp_data_list = []
    for hotel, base_rate in competitors.items():
        comp_df = generate_competitor_data(hotel, base_rate, volatility=0.12)
        comp_data_list.append(comp_df)
    
    competitor_df = pd.concat(comp_data_list, ignore_index=True)

    return full_df, rc_data, all_rc, yearly_summary, cat_summary, rate_mapping, events, competitor_df

df, rc_dict, all_rc, yearly_summary, cat_summary, rate_mapping, events, competitor_df = load_all_data()

# -----------------------------
# 4. Sidebar Profile & Control
# -----------------------------
asher_pic_base64 = get_image_base64("asher_picture.png")
github_url = "https://github.com/asherjc-creator/econo-revenue-dashboard"
email = "asher.charles@icloud.com"

with st.sidebar:
    if asher_pic_base64:
        st.markdown(
            f'<img src="{asher_pic_base64}" style="border-radius: 50%; width: 140px; height: 140px; object-fit: cover; display: block; margin: 0 auto 10px auto; border: 3px solid #eee;">',
            unsafe_allow_html=True
        )
    st.markdown("## Asher Jannu")
    st.markdown("### **Revenue Analyst**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<a href="{github_url}" target="_blank"><button style="background-color: #24292e; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; width: 100%;">GitHub</button></a>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f'<a href="mailto:{email}"><button style="background-color: #007bff; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; width: 100%;">Email</button></a>',
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
    
    if rate_mapping:
        st.markdown("---")
        st.caption(f"✅ Rate mapping: {len(rate_mapping)} codes")
        st.caption("📊 Competitors tracked: 7 hotels")

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
    cols = st.columns(len(yearly_summary))
    for i, (_, row) in enumerate(yearly_summary.iterrows()):
        with cols[i]:
            st.metric(
                f"{int(row['Year'])}",
                f"${row['Room_Revenue']:,.0f}",
                delta=f"{row['Occupancy%']:.1f}% Occ | ${row['ADR']:.0f} ADR"
            )

if not filtered.empty:
    st.write("### 📈 Selected Period KPIs")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Average ADR", f"${filtered['ADR'].mean():.2f}")
    k2.metric("Occupancy", f"{filtered['Occupancy'].mean()*100:.1f}%")
    k3.metric("RevPAR", f"${filtered['RevPAR'].mean():.2f}")
    k4.metric("Total Revenue", f"${filtered['Room_Revenue'].sum():,.0f}")

# -----------------------------
# 7. Competitor Rate Benchmarking 2026
# -----------------------------
st.divider()
st.header("🏨 Competitor Rate Benchmarking - 2026")
st.caption("5-Mile Radius | Arlington, VA Market")

comp_2026 = competitor_df[competitor_df['Date'].dt.year == 2026].copy()

if not comp_2026.empty:
    comp_2026['Month'] = comp_2026['Date'].dt.to_period('M')
    monthly_comp = comp_2026.groupby(['Month', 'Hotel'])['Rate'].mean().reset_index()
    monthly_comp['Month_Date'] = monthly_comp['Month'].dt.to_timestamp()
    
    fig_comp = px.line(
        monthly_comp,
        x='Month_Date',
        y='Rate',
        color='Hotel',
        title="2026 Competitor Rate Comparison (Monthly Average)",
        labels={'Rate': 'Average Daily Rate ($)', 'Month_Date': 'Month'},
        color_discrete_sequence=px.colors.qualitative.Set1
    )
    fig_comp.update_layout(height=450, hovermode='x unified')
    st.plotly_chart(fig_comp, use_container_width=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 Market Positioning")
        avg_rates = comp_2026.groupby('Hotel')['Rate'].agg(['mean', 'min', 'max']).round(0)
        avg_rates = avg_rates.sort_values('mean', ascending=False)
        avg_rates.columns = ['Avg Rate', 'Min Rate', 'Max Rate']
        st.dataframe(avg_rates, use_container_width=True)
    
    with col2:
        st.subheader("💰 Rate Premium/Discount Analysis")
        
        market_avg = comp_2026.groupby('Date')['Rate'].mean().reset_index()
        market_avg.columns = ['Date', 'Market_Avg']
        
        econo_rates = comp_2026[comp_2026['Hotel'] == 'Econo Lodge Metro Arlington'][['Date', 'Rate']]
        econo_rates = econo_rates.merge(market_avg, on='Date')
        econo_rates['Premium_vs_Market'] = econo_rates['Rate'] - econo_rates['Market_Avg']
        econo_rates['Month'] = econo_rates['Date'].dt.to_period('M')
        
        monthly_premium = econo_rates.groupby('Month')['Premium_vs_Market'].mean().reset_index()
        monthly_premium['Month_Date'] = monthly_premium['Month'].dt.to_timestamp()
        
        fig_premium = px.bar(
            monthly_premium,
            x='Month_Date',
            y='Premium_vs_Market',
            title="Econo Lodge Rate Premium vs Market Average",
            labels={'Premium_vs_Market': 'Premium ($)', 'Month_Date': 'Month'},
            color='Premium_vs_Market',
            color_continuous_scale=['red', 'yellow', 'green']
        )
        fig_premium.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_premium, use_container_width=True)
        
        avg_premium = econo_rates['Premium_vs_Market'].mean()
        st.metric(
            "Average Rate Position vs Market",
            f"${avg_premium:+.0f}",
            delta="Below Market Average" if avg_premium < 0 else "Above Market Average"
        )
    
    st.subheader("📍 Competitive Set Summary")
    comp_summary = comp_2026.groupby('Hotel').agg({
        'Rate': ['mean', 'std', 'count']
    }).round(2)
    comp_summary.columns = ['Avg Rate', 'Rate Volatility', 'Days']
    comp_summary = comp_summary.sort_values('Avg Rate', ascending=False)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Highest Priced Competitor", 
                  f"${comp_summary['Avg Rate'].max():.0f}",
                  f"{comp_summary.index[0]}")
    with c2:
        econo_rate = comp_summary.loc['Econo Lodge Metro Arlington', 'Avg Rate']
        econo_rank = comp_summary.index.tolist().index('Econo Lodge Metro Arlington') + 1
        st.metric("Econo Lodge Position", 
                  f"${econo_rate:.0f}",
                  f"Rank #{econo_rank} of {len(comp_summary)}")
    with c3:
        st.metric("Rate Gap to Leader", 
                  f"${comp_summary['Avg Rate'].max() - econo_rate:.0f}",
                  "Opportunity for rate growth")
    
    st.subheader("📅 Weekend vs Weekday Rate Comparison")
    comp_2026['Is_Weekend'] = comp_2026['Date'].dt.dayofweek >= 5
    weekend_comp = comp_2026.groupby(['Hotel', 'Is_Weekend'])['Rate'].mean().reset_index()
    weekend_pivot = weekend_comp.pivot(index='Hotel', columns='Is_Weekend', values='Rate')
    weekend_pivot.columns = ['Weekday', 'Weekend']
    weekend_pivot['Weekend_Premium'] = weekend_pivot['Weekend'] - weekend_pivot['Weekday']
    weekend_pivot['Premium_%'] = (weekend_pivot['Weekend_Premium'] / weekend_pivot['Weekday'] * 100).round(1)
    weekend_pivot = weekend_pivot.sort_values('Weekend_Premium', ascending=False)
    
    st.dataframe(weekend_pivot.style.format({
        'Weekday': '${:.0f}',
        'Weekend': '${:.0f}',
        'Weekend_Premium': '${:.0f}',
        'Premium_%': '{:.1f}%'
    }), use_container_width=True)

# -----------------------------
# 8. Rate Category Performance Analysis
# -----------------------------
st.divider()
st.header("📂 Rate Category Performance Analysis")

if not cat_summary.empty:
    col1, col2 = st.columns([2, 1])
    
    with col1:
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

# -----------------------------
# 9. 2025 Gap Analysis: ADR vs RevPAR
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

# -----------------------------
# 10. Rate Code Analysis - Top Performers
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

# -----------------------------
# 11. 2026 Reservation Activity Analysis
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

# -----------------------------
# 12. 90-Day Predictive Pricing
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
# 13. Heatmaps & Maps
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
# 14. AI Engine Query
# -----------------------------
st.write("---")
st.write("### 🤖 AI Pricing Recommendation Engine")

# Set the default check date to 14 days from the last data point
check_date = st.date_input(
    "Query a Specific Future Date:",
    forecast_start + timedelta(days=14),
    min_value=forecast_start.date()
)

# Convert the selected date to datetime for filtering
res = forecast_df[forecast_df["Date"] == pd.to_datetime(check_date)]

if not res.empty:
    row = res.iloc[0]
    st.metric(
        f"Recommended ADR: {check_date}",
        f"${row['Suggested_Rate']:.2f}",
        delta="Enforced $90 Floor"
    )
    
    # Display event warnings or success messages based on impact
    if row['Impact_Level'] != "None":
        st.warning(f"Event Detected: {row['Event']} ({row['Impact_Level']} Impact)")
    
    if row['Premium'] > 0:
        st.success(f"Premium +${row['Premium']:.0f} applied for this date.")
else:
    # This handles dates selected outside the 90-day forecast window
    st.info("The selected date is outside the current 90-day predictive window. Please select a date closer to the current period.")
