import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

# ------------------------------
# Page config
# ------------------------------
st.set_page_config(page_title="Hotel Performance Dashboard", layout="wide")
st.title("🏨 Econo Lodge Metro – April Year‑Over‑Year Analysis")

# ------------------------------
# Constants
# ------------------------------
TOTAL_ROOMS = 47
ESTIMATED_GOP_MARGIN = 0.40  # default, adjustable via slider
CURRENT_DATE_2026 = datetime(2026, 4, 11)  # today's date in 2026 context

# ------------------------------
# Helper functions
# ------------------------------
def clean_numeric(series):
    """Convert strings with commas/symbols to numbers."""
    if series.dtype == 'object':
        series = series.astype(str).str.replace(r'[$,%]', '', regex=True).str.strip()
    return pd.to_numeric(series, errors='coerce').fillna(0)

@st.cache_data
def load_and_clean_data():
    """Load all April CSV files and return a single DataFrame."""
    files = {
        '2023': 'APRIL 2023.csv',
        '2024': 'APRIL 2024.csv',
        '2025': 'APRIL 2025.csv',
        '2026': 'APRIL 2026.csv'
    }

    all_data = []
    for year, file in files.items():
        file_path = Path(file)
        if not file_path.exists():
            st.warning(f"File {file} not found. Skipping.")
            continue

        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')

            # Clean column names (remove BOM, quotes, spaces)
            df.columns = [
                c.replace('\ufeff', '').replace('"', '').strip()
                for c in df.columns
            ]

            # Rename date column for consistency
            df.rename(columns={'IDS_DATE': 'Date'}, inplace=True)

            # Convert Date
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])

            # Convert numeric columns
            df['RoomRev'] = clean_numeric(df['RoomRev'])
            df['OccPercent'] = clean_numeric(df['OccPercent'])
            df['ADR'] = clean_numeric(df['ADR'])
            df['RevPAR'] = clean_numeric(df['RevPAR'])
            df['Occupied'] = clean_numeric(df['Occupied'])

            df['Year'] = year
            all_data.append(df)

        except Exception as e:
            st.error(f"Error processing {file}: {e}")

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)

# ------------------------------
# Load data
# ------------------------------
df_full = load_and_clean_data()

if df_full.empty:
    st.error("No data loaded. Please check your CSV files.")
    st.stop()

# Add day of month for plotting
df_full['Day_of_Month'] = df_full['Date'].dt.day

# ------------------------------
# Sidebar controls
# ------------------------------
st.sidebar.header("📊 Dashboard Controls")

# Year selection
available_years = sorted(df_full['Year'].unique())
selected_years = st.sidebar.multiselect(
    "Select Years",
    options=available_years,
    default=['2024', '2025', '2026']
)

# GOP margin slider
gop_margin = st.sidebar.slider(
    "Estimated GOP Margin (%)",
    min_value=20,
    max_value=60,
    value=40,
    step=5
) / 100.0

# Recalculate GOP fields based on slider
df_full['Est_GOP'] = df_full['RoomRev'] * gop_margin
df_full['GOPPAR'] = df_full['Est_GOP'] / TOTAL_ROOMS

# ------------------------------
# Filter data based on selection
# ------------------------------
df_filtered = df_full[df_full['Year'].isin(selected_years)].copy()

if df_filtered.empty:
    st.warning("No data for the selected years.")
    st.stop()

# Determine "latest" year for metric display (prefer 2026 if selected)
if '2026' in selected_years:
    latest_year = '2026'
else:
    latest_year = max(selected_years)

current_df = df_filtered[df_filtered['Year'] == latest_year]

# For 2026, only include actuals up to CURRENT_DATE_2026
if latest_year == '2026':
    display_df = current_df[current_df['Date'] <= CURRENT_DATE_2026]
    st.info(f"💡 Metrics for 2026 are based on actuals through {CURRENT_DATE_2026.strftime('%b %d, %Y')}.")
else:
    display_df = current_df

# ------------------------------
# Main dashboard
# ------------------------------
# ---- KPI Row ----
st.subheader(f"📈 Key Metrics – {latest_year} (YTD through April 11 if 2026)")
cols = st.columns(4)
with cols[0]:
    st.metric("Avg Occupancy", f"{display_df['OccPercent'].mean():.1f}%")
with cols[1]:
    st.metric("Avg ADR", f"${display_df['ADR'].mean():.2f}")
with cols[2]:
    st.metric("Avg RevPAR", f"${display_df['RevPAR'].mean():.2f}")
with cols[3]:
    st.metric("Avg GOPPAR (Est.)", f"${display_df['GOPPAR'].mean():.2f}")

# ---- Year-over-Year Comparison Charts ----
st.subheader("📊 Year‑over‑Year Comparison")
agg_df = df_filtered.groupby('Year').agg({
    'RoomRev': 'sum',
    'OccPercent': 'mean',
    'ADR': 'mean',
    'RevPAR': 'mean',
    'Occupied': 'sum',
    'Est_GOP': 'sum',
    'GOPPAR': 'mean'
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

# ---- Daily Trend (Line Chart) ----
st.subheader("📅 Daily Performance Trends")
metric_choice = st.selectbox(
    "Select metric for daily trend",
    options=['OccPercent', 'ADR', 'RevPAR', 'RoomRev', 'GOPPAR'],
    format_func=lambda x: {
        'OccPercent': 'Occupancy %',
        'ADR': 'ADR ($)',
        'RevPAR': 'RevPAR ($)',
        'RoomRev': 'Room Revenue ($)',
        'GOPPAR': 'GOPPAR ($)'
    }.get(x, x)
)

fig_line = px.line(
    df_filtered,
    x='Day_of_Month',
    y=metric_choice,
    color='Year',
    title=f"April {metric_choice} Daily Trends",
    labels={'Day_of_Month': 'Day of Month', metric_choice: metric_choice},
    template="plotly_white"
)

# Add vertical line for April 11 in 2026 if 2026 is selected
if '2026' in selected_years:
    fig_line.add_vline(
        x=CURRENT_DATE_2026.day,
        line_dash="dash",
        line_color="orange",
        annotation_text=f"Today (Apr {CURRENT_DATE_2026.day})",
        annotation_position="top"
    )

st.plotly_chart(fig_line, use_container_width=True)

# ---- Heatmap: Occupancy by Day and Year ----
st.subheader("🔥 Occupancy Heatmap (Day vs Year)")
pivot = df_filtered.pivot_table(
    index='Day_of_Month',
    columns='Year',
    values='OccPercent',
    aggfunc='mean'
)
fig_heat = px.imshow(
    pivot,
    text_auto='.1f',
    aspect="auto",
    title="Occupancy % – Day of Month vs Year",
    labels=dict(x="Year", y="Day of Month", color="Occupancy %"),
    color_continuous_scale="Blues"
)
st.plotly_chart(fig_heat, use_container_width=True)

# ---- Financial Summary Table ----
st.subheader("💰 Monthly Financial Performance Summary")
summary = df_filtered.groupby('Year').agg({
    'RoomRev': 'sum',
    'Est_GOP': 'sum',
    'RevPAR': 'mean',
    'GOPPAR': 'mean',
    'OccPercent': 'mean',
    'ADR': 'mean'
}).reset_index()

st.dataframe(
    summary.style.format({
        'RoomRev': '${:,.0f}',
        'Est_GOP': '${:,.0f}',
        'RevPAR': '${:.2f}',
        'GOPPAR': '${:.2f}',
        'OccPercent': '{:.1f}%',
        'ADR': '${:.2f}'
    }),
    use_container_width=True
)

# ---- Storytelling Insights (auto-generated) ----
st.subheader("📝 Quick Insights")
if '2026' in selected_years and len(selected_years) > 1:
    # Compare 2026 YTD vs same period in previous years
    # First, get day-of-month cutoff
    cutoff_day = CURRENT_DATE_2026.day
    # Filter all years to same day range for fair comparison
    ytd_df = df_filtered[df_filtered['Day_of_Month'] <= cutoff_day]
    ytd_agg = ytd_df.groupby('Year').agg({
        'OccPercent': 'mean',
        'ADR': 'mean',
        'RevPAR': 'mean',
        'RoomRev': 'sum'
    }).reset_index()

    avg_2026_occ = ytd_agg[ytd_agg['Year'] == '2026']['OccPercent'].values[0]
    avg_others_occ = ytd_agg[ytd_agg['Year'] != '2026']['OccPercent'].mean()
    occ_change = avg_2026_occ - avg_others_occ

    avg_2026_adr = ytd_agg[ytd_agg['Year'] == '2026']['ADR'].values[0]
    avg_others_adr = ytd_agg[ytd_agg['Year'] != '2026']['ADR'].mean()
    adr_change = avg_2026_adr - avg_others_adr

    st.markdown(f"""
    - **Occupancy YTD (Apr 1‑11):** 2026 is **{avg_2026_occ:.1f}%** vs. prior years' average **{avg_others_occ:.1f}%**  
      → { '📈 Increase' if occ_change > 0 else '📉 Decrease' } of **{abs(occ_change):.1f} pp**.
    - **ADR YTD:** 2026 is **${avg_2026_adr:.2f}** vs. prior years' average **${avg_others_adr:.2f}**  
      → { '📈 Increase' if adr_change > 0 else '📉 Decrease' } of **${abs(adr_change):.2f}**.
    """)
else:
    st.markdown("Select 2026 along with other years to see year‑over‑year insights for the current month‑to‑date period.")

# ---- Raw Data Expander ----
with st.expander("📋 View Raw Data"):
    st.dataframe(df_filtered.sort_values('Date'), use_container_width=True)

st.caption("Data source: April 2023–2026 CSV files. GOP is estimated based on slider margin.")
