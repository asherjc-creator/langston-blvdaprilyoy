import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ------------------------------
# Page config
# ------------------------------
st.set_page_config(page_title="Hotel Performance Dashboard", layout="wide")
st.title("🏨 Hotel Performance Dashboard – April 2023–2026")

# ------------------------------
# Helper functions
# ------------------------------
@st.cache_data
def load_all_data():
    """Load all April CSV files and return a single DataFrame with a 'Year' column."""
    years = [2023, 2024, 2025, 2026]
    dfs = []
    for year in years:
        file_path = Path(f"APRIL {year}.csv")
        if file_path.exists():
            df = pd.read_csv(file_path, encoding='utf-8-sig')  # handles BOM
            # Clean column names (remove spaces, quotes, etc.)
            df.columns = df.columns.str.strip().str.replace('"', '').str.replace(' ', '')
            # Convert date column
            df['IDS_DATE'] = pd.to_datetime(df['IDS_DATE'])
            # Convert percentage strings to float
            if 'OccPercent' in df.columns:
                df['OccPercent'] = df['OccPercent'].str.replace('%', '').str.strip().astype(float)
            # Ensure numeric columns are float
            numeric_cols = ['RoomRev', 'RevPAR', 'ADR', 'Occupied', 'Available', 'Rooms']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df['Year'] = year
            dfs.append(df)
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()

def compute_kpis(df):
    """Return a dictionary of aggregated KPIs for the filtered data."""
    total_revenue = df['RoomRev'].sum()
    avg_occupancy = df['OccPercent'].mean()
    avg_adr = df['ADR'].mean()
    avg_revpar = df['RevPAR'].mean()
    total_room_nights = df['Occupied'].sum()
    return {
        'Total Room Revenue': f"${total_revenue:,.0f}",
        'Avg Occupancy': f"{avg_occupancy:.1f}%",
        'Avg ADR': f"${avg_adr:.2f}",
        'Avg RevPAR': f"${avg_revpar:.2f}",
        'Room Nights Sold': f"{total_room_nights:.0f}"
    }

# ------------------------------
# Load data
# ------------------------------
df_all = load_all_data()

if df_all.empty:
    st.error("No data files found. Please ensure CSV files are in the same directory.")
    st.stop()

# ------------------------------
# Sidebar controls
# ------------------------------
st.sidebar.header("Filters")

# Month selector (currently only April available, but ready for extension)
available_months = df_all['IDS_DATE'].dt.month_name().unique()
default_month = "April"
selected_month = st.sidebar.selectbox(
    "Select Month",
    options=available_months,
    index=list(available_months).index(default_month) if default_month in available_months else 0
)

# Year multiselect
available_years = sorted(df_all['Year'].unique())
selected_years = st.sidebar.multiselect(
    "Select Years",
    options=available_years,
    default=available_years  # all years by default
)

# Filter data based on selection
mask = (df_all['IDS_DATE'].dt.month_name() == selected_month) & (df_all['Year'].isin(selected_years))
df_filtered = df_all[mask].copy()

if df_filtered.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# ------------------------------
# Main dashboard
# ------------------------------
# ---- KPI Row ----
st.subheader(f"📊 Key Metrics – {selected_month} {', '.join(map(str, selected_years))}")
kpis = compute_kpis(df_filtered)

cols = st.columns(len(kpis))
for col, (label, value) in zip(cols, kpis.items()):
    with col:
        st.metric(label, value)

# ---- Year-over-Year Comparison (aggregated) ----
st.subheader("📈 Year-over-Year Comparison")
agg_df = df_filtered.groupby('Year').agg({
    'RoomRev': 'sum',
    'OccPercent': 'mean',
    'ADR': 'mean',
    'RevPAR': 'mean',
    'Occupied': 'sum'
}).reset_index()

col1, col2 = st.columns(2)
with col1:
    fig_rev = px.bar(agg_df, x='Year', y='RoomRev', text_auto='.2s',
                     title="Total Room Revenue by Year",
                     labels={'RoomRev': 'Revenue ($)'})
    fig_rev.update_traces(textposition='outside')
    st.plotly_chart(fig_rev, use_container_width=True)

    fig_occ = px.bar(agg_df, x='Year', y='OccPercent', text_auto='.1f',
                     title="Average Occupancy % by Year",
                     labels={'OccPercent': 'Occupancy (%)'})
    fig_occ.update_traces(textposition='outside')
    st.plotly_chart(fig_occ, use_container_width=True)

with col2:
    fig_adr = px.bar(agg_df, x='Year', y='ADR', text_auto='.2s',
                     title="Average ADR by Year",
                     labels={'ADR': 'ADR ($)'})
    fig_adr.update_traces(textposition='outside')
    st.plotly_chart(fig_adr, use_container_width=True)

    fig_revpar = px.bar(agg_df, x='Year', y='RevPAR', text_auto='.2s',
                        title="Average RevPAR by Year",
                        labels={'RevPAR': 'RevPAR ($)'})
    fig_revpar.update_traces(textposition='outside')
    st.plotly_chart(fig_revpar, use_container_width=True)

# ---- Daily Trends (line charts) ----
st.subheader("📅 Daily Performance Trends")
metric_choice = st.selectbox("Select metric to view daily trend",
                             options=['OccPercent', 'ADR', 'RevPAR', 'RoomRev'],
                             format_func=lambda x: {
                                 'OccPercent': 'Occupancy %',
                                 'ADR': 'ADR ($)',
                                 'RevPAR': 'RevPAR ($)',
                                 'RoomRev': 'Room Revenue ($)'
                             }.get(x, x))

fig_line = px.line(df_filtered, x='IDS_DATE', y=metric_choice, color='Year',
                   title=f"Daily {metric_choice} – {selected_month}",
                   labels={'IDS_DATE': 'Date', metric_choice: metric_choice})
fig_line.update_layout(hovermode='x unified')
st.plotly_chart(fig_line, use_container_width=True)

# ---- Heatmap: Occupancy by Day of Month and Year ----
st.subheader("🔥 Occupancy Heatmap (Day vs Year)")
df_filtered['DayOfMonth'] = df_filtered['IDS_DATE'].dt.day
pivot = df_filtered.pivot_table(index='DayOfMonth', columns='Year', values='OccPercent', aggfunc='mean')
fig_heat = px.imshow(pivot, text_auto='.1f', aspect="auto",
                     title="Occupancy % – Day of Month vs Year",
                     labels=dict(x="Year", y="Day of Month", color="Occupancy %"))
st.plotly_chart(fig_heat, use_container_width=True)

# ---- Data table (optional) ----
with st.expander("📋 View Raw Data"):
    st.dataframe(df_filtered.sort_values('IDS_DATE'), use_container_width=True)

# ---- Storytelling Insights (auto-generated) ----
st.subheader("📝 Quick Insights")
# Compare 2026 vs previous years average
if 2026 in selected_years and len(selected_years) > 1:
    avg_2026_occ = agg_df[agg_df['Year']==2026]['OccPercent'].values[0]
    avg_others_occ = agg_df[agg_df['Year']!=2026]['OccPercent'].mean()
    occ_change = avg_2026_occ - avg_others_occ

    avg_2026_adr = agg_df[agg_df['Year']==2026]['ADR'].values[0]
    avg_others_adr = agg_df[agg_df['Year']!=2026]['ADR'].mean()
    adr_change = avg_2026_adr - avg_others_adr

    st.markdown(f"""
    - **Occupancy in 2026** is **{avg_2026_occ:.1f}%** vs. previous years' average of **{avg_others_occ:.1f}%**  
      → { '📈 Increase' if occ_change > 0 else '📉 Decrease' } of **{abs(occ_change):.1f} pp**.
    - **ADR in 2026** is **${avg_2026_adr:.2f}** vs. previous years' average of **${avg_others_adr:.2f}**  
      → { '📈 Increase' if adr_change > 0 else '📉 Decrease' } of **${abs(adr_change):.2f}**.
    """)
else:
    st.markdown("Select multiple years (including 2026) to see year‑over‑year insights.")

st.caption("Data source: April 2023–2026 CSV files. Dashboard built with Streamlit.")