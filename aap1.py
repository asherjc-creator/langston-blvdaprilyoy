import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="2026 Revenue Recovery Portal",
    layout="wide",
    page_icon="🏨"
)

# -----------------------------
# Custom Styling
# -----------------------------
st.markdown("""
<style>
    .main { background-color:#f8f9fa; }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .strategy-container {
        background-color: #eef4ff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #007bff;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Data Definition
# -----------------------------

@st.cache_data
def get_revenue_data():
    # 1. 3-Year KPI Comparison (Based on Strategy PDF/User Inputs)
    # Focused on Q2 (April-June) Baseline Comparison
    kpi_data = pd.DataFrame({
        "Year": [2024, 2025, 2026],
        "ADR": [109.68, 97.57, 121.55],
        "RevPAR": [121.22, 109.19, 30.95],
        "OCC%": [90.5, 89.4, 25.5],
        "Rooms_Revenue": [485230, 412500, 115200]
    })

    # 2. Rate Code Performance Table (User Provided Data)
    rate_codes = pd.DataFrame([
        ["SO2BK", 60631, "Performing", "Disappeared"],
        ["SO1R", 35596, "Disappeared", "Disappeared"],
        ["SOPM1M", 34228, "Disappeared", "Disappeared"],
        ["SO2R", 29754, "Performing", "Disappeared"],
        ["SO1EXP", 27177, "Disappeared", "Disappeared"],
        ["GROUP~", 22739, "Underperforming", "Disappeared"]
    ], columns=["Rate Code", "2024 Revenue", "Status 2025", "Status 2026"])

    # 3. Gap Analysis for 2025
    gap_analysis = pd.DataFrame({
        "Quarter": ["Q1", "Q2", "Q3", "Q4"],
        "ADR_Gap": [13.08, -12.11, -30.71, -10.47],
        "Rev_Leakage": [-31569, -51785, -132806, -49385]
    })
    
    return kpi_data, rate_codes, gap_analysis

kpi_df, rate_df, gap_df = get_revenue_data()

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("Asher Jannu")
    st.caption("Revenue Analyst")
    st.write("---")
    st.subheader("Global Controls")
    selected_view = st.radio("Navigation", ["3-Year KPIs", "Rate Code Analysis", "0-7 Day Roadmap"])
    st.write("---")
    st.info("Goal: Rebalance pricing to ~$109 ADR to recover volume.")

# -----------------------------
# Header
# -----------------------------
st.title("📈 2026 Strategic Revenue Recovery")
st.markdown("### Objective: Achieve 2024 Revenue Benchmarks via Pricing Realignment")

# -----------------------------
# Section 1: Dashboard KPI Comparison
# -----------------------------
st.header("1. Dashboard KPI Comparison (2024 vs 2025 vs 2026)")

# Metric Row
m1, m2, m3, m4 = st.columns(4)
current = kpi_df[kpi_df['Year'] == 2026].iloc[0]
baseline = kpi_df[kpi_df['Year'] == 2024].iloc[0]

m1.metric("Current ADR", f"${current['ADR']:.2f}", delta=f"{current['ADR'] - baseline['ADR']:.2f} (High Rate)")
m2.metric("Current RevPAR", f"${current['RevPAR']:.2f}", delta=f"{current['RevPAR'] - baseline['RevPAR']:.2f}", delta_color="inverse")
m3.metric("Current OCC%", f"{current['OCC%']}%", delta=f"{current['OCC%'] - baseline['OCC%']:.1f}%", delta_color="inverse")
m4.metric("Rooms Revenue", f"${current['Rooms_Revenue']:,.0f}", delta=f"${current['Rooms_Revenue'] - baseline['Rooms_Revenue']:,.0f}", delta_color="inverse")

# 3-Year Comparison Chart
fig_yoy = go.Figure()
fig_yoy.add_trace(go.Bar(x=kpi_df['Year'].astype(str), y=kpi_df['Rooms_Revenue'], name='Rooms Revenue', marker_color='#007bff'))
fig_yoy.add_trace(go.Scatter(x=kpi_df['Year'].astype(str), y=kpi_df['ADR'] * 1000, name='ADR Trend (Scaled)', line=dict(color='#ff7f0e', width=4)))

fig_yoy.update_layout(title="Revenue vs Rate Positioning (2024-2026)", hovermode="x unified")
st.plotly_chart(fig_yoy, use_container_width=True)

# -----------------------------
# Section 2: Rate Code & Gap Analysis
# -----------------------------
st.write("---")
col_a, col_b = st.columns([1.5, 1])

with col_a:
    st.header("2. Rate Code Performance (Leakage Audit)")
    
    # Custom styling function for the table
    def style_status(val):
        if val == "Disappeared": return 'color: #d9534f; font-weight: bold;'
        if val == "Performing": return 'color: #5cb85c; font-weight: bold;'
        if val == "Underperforming": return 'color: #f0ad4e; font-weight: bold;'
        return ''

    # Applying the new .map() method for Pandas 2.1.0+
    styled_df = rate_df.style.map(style_status, subset=['Status 2025', 'Status 2026'])\
                         .format({"2024 Revenue": "${:,.0f}"})
    
    st.table(styled_df)
    st.error("Action Required: Investigate SO2BK and SO1R—Lost contribution exceeds $96k.")

with col_b:
    st.header("2025 Gap Analysis")
    fig_gap = px.bar(gap_df, x='Quarter', y='Rev_Leakage', 
                     title="Revenue Loss by Quarter (2025)",
                     color='Rev_Leakage', color_continuous_scale='Reds_r')
    st.plotly_chart(fig_gap, use_container_width=True)

# -----------------------------
# Section 3: 0-7 Day Strategy Roadmap
# -----------------------------
st.write("---")
st.header("3. 0-7 Day Execution Roadmap")

roadmap = pd.DataFrame([
    ["Day 0-2", "Immediate Rate Drop", "Lower Q2 floor by 10-18% to capture market volume.", "Revenue Mgr"],
    ["Day 0-2", "Rate Code Audit", "Investigate why SO2BK and SO1R are inactive.", "Tech/Ops"],
    ["Day 3-5", "Launch Promo", "Activate 'Stay 2, Save 20%' via GDS and Web channels.", "Marketing"],
    ["Day 5-7", "Segment Reactivation", "Ensure SO2R and SO1EXP are delivering to OTAs.", "Revenue Team"]
], columns=["Timeframe", "Priority Task", "Description", "Stakeholder"])

st.table(roadmap)

st.markdown("""
<div class="strategy-container">
    <h4>💡 Strategic Summary</h4>
    The current 2026 ADR of <b>$121.55</b> is yielding only <b>25.5% occupancy</b>. 
    By lowering the target ADR to <b>$109</b>, we project an occupancy recovery to <b>75-80%</b>, 
    effectively regaining the revenue levels seen in the 2024 benchmark.
</div>
""", unsafe_allow_html=True)
