import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from pathlib import Path

# ------------------------------
# Page Configuration
# ------------------------------
st.set_page_config(
    page_title="Hotel Performance Dashboard",
    page_icon="🏨",
    layout="wide"
)

# ------------------------------
# Constants
# ------------------------------
TOTAL_ROOMS = 47
CURRENT_DATE_2026 = datetime(2026, 4, 11)  # YTD context for 2026

# ------------------------------
# Helper Functions
# ------------------------------
def clean_numeric(series):
    """Convert strings with symbols to numeric values."""
    if series.dtype == 'object':
        series = series.astype(str).str.replace(r'[$,%]', '', regex=True).str.strip()
    return pd.to_numeric(series, errors='coerce').fillna(0)

@st.cache_data
def load_and_clean_data():
    """Load all CSV files and return a unified DataFrame."""
    files = {
        '2023': 'APRIL 2023.csv',
        '2024': 'APRIL 2024.csv',
        '2025': 'APRIL 2025.csv',
        '2026': 'APRIL 2026.csv'
    }

    all_data = []
    for year, filename in files.items():
        file_path = Path(filename)
        if not file_path.exists():
            continue

        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            # Clean column names
            df.columns = [
                c.replace('\ufeff', '').replace('"', '').strip()
                for c in df.columns
            ]
            # Standardize date column
            df.rename(columns={'IDS_DATE': 'Date'}, inplace=True)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])

            # Convert numeric columns
            numeric_cols = ['RoomRev', 'OccPercent', 'ADR', 'RevPAR', 'Occupied']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = clean_numeric(df[col])

            df['Year'] = year
            all_data.append(df)

        except Exception as e:
            st.error(f"Error reading {filename}: {e}")

    if not all_data:
        return pd.DataFrame()

    df_full = pd.concat(all_data, ignore_index=True)
    df_full['Day_of_Month'] = df_full['Date'].dt.day
    df_full['Weekday'] = df_full['Date'].dt.day_name()
    return df_full

# ------------------------------
# Load Data
# ------------------------------
df_all = load_and_clean_data()

if df_all.empty:
    st.error("No data found. Please ensure CSV files are in the same directory.")
    st.stop()

# ------------------------------
# Sidebar Controls
# ------------------------------
st.sidebar.header("📊 Dashboard Controls")

# Month selector (default April)
available_months = df_all['Date'].dt.month_name().unique()
default_month = "April" if "April" in available_months else available_months[0]
selected_month = st.sidebar.selectbox("Select Month", options=available_months, index=list(available_months).index(default_month))

# Year multiselect
available_years = sorted(df_all['Year'].unique())
selected_years = st.sidebar.multiselect("Select Years", options=available_years, default=available_years)

# GOP margin slider
gop_margin = st.sidebar.slider("Estimated GOP Margin (%)", 20, 60, 40, step=5) / 100

# Filter data
mask = (df_all['Date'].dt.month_name() == selected_month) & (df_all['Year'].isin(selected_years))
df = df_all[mask].copy()

if df.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# Add GOP calculations
df['Est_GOP'] = df['RoomRev'] * gop_margin
df['GOPPAR'] = df['Est_GOP'] / TOTAL_ROOMS

# ------------------------------
# Header & KPI Row
# ------------------------------
st.title(f" Hotel Performance Dashboard – {selected_month} {', '.join(selected_years)}")

# Determine latest year for KPI display
latest_year = '2026' if '2026' in selected_years else max(selected_years)
current_df = df[df['Year'] == latest_year]

if latest_year == '2026':
    display_df = current_df[current_df['Date'] <= CURRENT_DATE_2026]
    st.info(f"💡 Metrics for 2026 are based on actuals through {CURRENT_DATE_2026.strftime('%b %d, %Y')}.")
else:
    display_df = current_df

cols = st.columns(4)
with cols[0]:
    st.metric("Avg Occupancy", f"{display_df['OccPercent'].mean():.1f}%")
with cols[1]:
    st.metric("Avg ADR", f"${display_df['ADR'].mean():.2f}")
with cols[2]:
    st.metric("Avg RevPAR", f"${display_df['RevPAR'].mean():.2f}")
with cols[3]:
    st.metric("Avg GOPPAR (Est.)", f"${display_df['GOPPAR'].mean():.2f}")

st.divider()

# ------------------------------
# Year-over-Year Comparison (Bar Charts)
# ------------------------------
st.subheader("📈 Year‑over‑Year Performance")
agg_df = df.groupby('Year').agg({
    'RoomRev': 'sum',
    'OccPercent': 'mean',
    'ADR': 'mean',
    'RevPAR': 'mean',
    'GOPPAR': 'mean',
    'Occupied': 'sum'
}).reset_index()

col1, col2 = st.columns(2)
with col1:
    fig_rev = px.bar(agg_df, x='Year', y='RoomRev', text_auto='.2s',
                     title="Total Room Revenue",
                     labels={'RoomRev': 'Revenue ($)'},
                     color_discrete_sequence=['#1f77b4'])
    fig_rev.update_traces(textposition='outside')
    st.plotly_chart(fig_rev, use_container_width=True)

    fig_occ = px.bar(agg_df, x='Year', y='OccPercent', text_auto='.1f',
                     title="Average Occupancy %",
                     labels={'OccPercent': 'Occupancy (%)'},
                     color_discrete_sequence=['#2ca02c'])
    fig_occ.update_traces(textposition='outside')
    st.plotly_chart(fig_occ, use_container_width=True)

with col2:
    fig_adr = px.bar(agg_df, x='Year', y='ADR', text_auto='.2s',
                     title="Average ADR",
                     labels={'ADR': 'ADR ($)'},
                     color_discrete_sequence=['#ff7f0e'])
    fig_adr.update_traces(textposition='outside')
    st.plotly_chart(fig_adr, use_container_width=True)

    fig_revpar = px.bar(agg_df, x='Year', y='RevPAR', text_auto='.2s',
                        title="Average RevPAR",
                        labels={'RevPAR': 'RevPAR ($)'},
                        color_discrete_sequence=['#d62728'])
    fig_revpar.update_traces(textposition='outside')
    st.plotly_chart(fig_revpar, use_container_width=True)

st.divider()

# ------------------------------
# Daily Performance Analysis
# ------------------------------
st.subheader("📅 Daily Performance Analysis")

# Combined chart: Room Revenue (bar) + Occupancy (line)
fig_combo = make_subplots(specs=[[{"secondary_y": True}]])
for year in selected_years:
    year_df = df[df['Year'] == year]
    fig_combo.add_trace(
        go.Bar(x=year_df['Day_of_Month'], y=year_df['RoomRev'], name=f"{year} Revenue", opacity=0.7),
        secondary_y=False
    )
    fig_combo.add_trace(
        go.Scatter(x=year_df['Day_of_Month'], y=year_df['OccPercent'], name=f"{year} Occupancy",
                   mode='lines+markers', line=dict(width=3)),
        secondary_y=True
    )

fig_combo.update_layout(
    title="Daily Room Revenue (Bars) vs Occupancy % (Lines)",
    xaxis_title="Day of Month",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
fig_combo.update_yaxes(title_text="Room Revenue ($)", secondary_y=False)
fig_combo.update_yaxes(title_text="Occupancy (%)", secondary_y=True)

# Add vertical line for April 11 if 2026 selected
if '2026' in selected_years:
    fig_combo.add_vline(x=CURRENT_DATE_2026.day, line_dash="dash", line_color="gray",
                        annotation_text="Apr 11", annotation_position="top")

st.plotly_chart(fig_combo, use_container_width=True)

# Day‑of‑week average performance
st.subheader("📊 Average Performance by Day of Week")
dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
dow_df = df.groupby(['Year', 'Weekday'], as_index=False).agg({
    'OccPercent': 'mean',
    'ADR': 'mean',
    'RevPAR': 'mean',
    'GOPPAR': 'mean'
})
dow_df['Weekday'] = pd.Categorical(dow_df['Weekday'], categories=dow_order, ordered=True)
dow_df = dow_df.sort_values(['Year', 'Weekday'])

fig_dow = px.line(dow_df, x='Weekday', y='RevPAR', color='Year', markers=True,
                  title="RevPAR by Day of Week",
                  labels={'RevPAR': 'RevPAR ($)'})
st.plotly_chart(fig_dow, use_container_width=True)

# Occupancy Heatmap
st.subheader("🔥 Occupancy Heatmap (Day of Month vs Year)")
pivot = df.pivot_table(index='Day_of_Month', columns='Year', values='OccPercent', aggfunc='mean')
fig_heat = px.imshow(pivot, text_auto='.1f', aspect="auto",
                     title="Occupancy % – Day of Month vs Year",
                     labels=dict(x="Year", y="Day of Month", color="Occupancy %"),
                     color_continuous_scale="Blues")
st.plotly_chart(fig_heat, use_container_width=True)

# ------------------------------
# Financial Summary Table
# ------------------------------
st.subheader("💰 Monthly Financial Summary")
summary = df.groupby('Year').agg({
    'RoomRev': 'sum',
    'Est_GOP': 'sum',
    'RevPAR': 'mean',
    'GOPPAR': 'mean',
    'OccPercent': 'mean',
    'ADR': 'mean',
    'Occupied': 'sum'
}).reset_index()

st.dataframe(
    summary.style.format({
        'RoomRev': '${:,.0f}',
        'Est_GOP': '${:,.0f}',
        'RevPAR': '${:.2f}',
        'GOPPAR': '${:.2f}',
        'OccPercent': '{:.1f}%',
        'ADR': '${:.2f}',
        'Occupied': '{:.0f}'
    }),
    use_container_width=True
)

# ------------------------------
# Storytelling Insights
# ------------------------------
st.subheader("📝 Quick Insights")
if '2026' in selected_years and len(selected_years) > 1:
    cutoff_day = CURRENT_DATE_2026.day
    ytd_df = df[df['Day_of_Month'] <= cutoff_day]
    ytd_agg = ytd_df.groupby('Year').agg({'OccPercent': 'mean', 'ADR': 'mean', 'RevPAR': 'mean'}).reset_index()

    occ_2026 = ytd_agg[ytd_agg['Year'] == '2026']['OccPercent'].values[0]
    occ_others = ytd_agg[ytd_agg['Year'] != '2026']['OccPercent'].mean()
    occ_change = occ_2026 - occ_others

    adr_2026 = ytd_agg[ytd_agg['Year'] == '2026']['ADR'].values[0]
    adr_others = ytd_agg[ytd_agg['Year'] != '2026']['ADR'].mean()
    adr_change = adr_2026 - adr_others

    st.markdown(f"""
    - **Occupancy YTD (Apr 1‑{cutoff_day})**: 2026 is **{occ_2026:.1f}%** vs. prior years avg **{occ_others:.1f}%**  
      → { '📈 Increase' if occ_change > 0 else '📉 Decrease' } of **{abs(occ_change):.1f} pp**.
    - **ADR YTD**: 2026 is **${adr_2026:.2f}** vs. prior years avg **${adr_others:.2f}**  
      → { '📈 Increase' if adr_change > 0 else '📉 Decrease' } of **${abs(adr_change):.2f}**.
    """)
else:
    st.markdown("Select 2026 along with other years to see MTD comparisons.")

# ------------------------------
# Raw Data Expander
# ------------------------------
with st.expander("📋 View Raw Data"):
    st.dataframe(df.sort_values('Date'), use_container_width=True)

st.caption("Data source: April 2023–2026 CSV files. GOP is estimated based on slider margin.")
