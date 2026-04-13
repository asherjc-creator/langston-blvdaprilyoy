import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
from io import BytesIO
import base64

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="Revenue Recovery Portal | 2026 Strategy",
    layout="wide",
    page_icon="📈"
)

# -----------------------------
# Custom Styling
# -----------------------------
st.markdown("""
<style>
    .main { background-color:#f8f9fa; }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eef0f2;
    }
    .strategy-box {
        background-color: #f0f7ff;
        padding: 20px;
        border-radius: 10px;
        border-left: 6px solid #007bff;
        margin-bottom: 20px;
    }
    .status-decline { color: #d9534f; font-weight: bold; }
    .status-growth { color: #5cb85c; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Data Definition (Extracted from Strategy PDF)
# -----------------------------
@st.cache_data
def get_dashboard_data():
    # YOY KPI Data
    kpi_data = pd.DataFrame([
        {"Quarter": "Q1", "Year": 2024, "Occ%": 82.3, "ADR": 83.10, "RevPAR": 68.42, "Status": "Benchmark"},
        {"Quarter": "Q1", "Year": 2025, "Occ%": 64.2, "ADR": 96.18, "RevPAR": 61.71, "Status": "Rate > Volume"},
        {"Quarter": "Q1", "Year": 2026, "Occ%": 51.4, "ADR": 95.56, "RevPAR": 49.13, "Status": "Current"},
        {"Quarter": "Q2", "Year": 2024, "Occ%": 90.5, "ADR": 121.22, "RevPAR": 109.68, "Status": "Peak"},
        {"Quarter": "Q2", "Year": 2025, "Occ%": 89.4, "ADR": 109.19, "RevPAR": 97.57, "Status": "Strong"},
        {"Quarter": "Q2", "Year": 2026, "Occ%": 25.5, "ADR": 121.55, "RevPAR": 30.95, "Status": "Critical Gap"}
    ])

    # 2025 Gap Analysis
    gap_data = pd.DataFrame([
        {"Quarter": "Q1", "ADR_Gap": 13.08, "RevPAR_Gap": -6.70, "Rev_Loss": -31569, "Cause": "Overpricing reduced demand"},
        {"Quarter": "Q2", "ADR_Gap": -12.11, "RevPAR_Gap": -12.03, "Rev_Loss": -51785, "Cause": "Lower rates didn't drive volume"},
        {"Quarter": "Q3", "ADR_Gap": -30.71, "RevPAR_Gap": -6.17, "Rev_Loss": -132806, "Cause": "Major volume collapse"},
        {"Quarter": "Q4", "ADR_Gap": -10.47, "RevPAR_Gap": -11.42, "Rev_Loss": -49385, "Cause": "Weak demand + rate cuts"}
    ])
    
    return kpi_data, gap_data

kpi_df, gap_df = get_dashboard_data()

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/144/hotel.png", width=100)
    st.title("Asher Jannu")
    st.markdown("### **Revenue Analyst**")
    st.write("---")
    selected_year = st.multiselect("Filter Years", [2024, 2025, 2026], default=[2024, 2025, 2026])
    st.info("Focus: Q2 2026 Recovery Strategy")

# -----------------------------
# Header
# -----------------------------
st.title("🏨 Quarterly YOY KPI Analysis & 2026 Recovery")
st.markdown(f"**Data Status:** Immediate action required for Q2 revenue leakage prevention.")

# -----------------------------
# Section 1: KPIs YOY
# -----------------------------
st.header("1. Performance Metrics (YOY)")
m1, m2, m3 = st.columns(3)

latest_q2 = kpi_df[(kpi_df['Quarter'] == 'Q2') & (kpi_df['Year'] == 2026)].iloc[0]
prev_q2 = kpi_df[(kpi_df['Quarter'] == 'Q2') & (kpi_df['Year'] == 2025)].iloc[0]

m1.metric("Q2 2026 ADR", f"${latest_q2['ADR']}", delta=f"{latest_q2['ADR'] - prev_q2['ADR']:.2f} (High Rate)")
m2.metric("Q2 2026 Occupancy", f"{latest_q2['Occ%']}%", delta=f"{latest_q2['Occ%'] - prev_q2['Occ%']:.1f}%", delta_color="inverse")
m3.metric("Q2 2026 RevPAR", f"${latest_q2['RevPAR']}", delta=f"{latest_q2['RevPAR'] - prev_q2['RevPAR']:.2f}", delta_color="inverse")

# Chart: RevPAR & Occ Trends
fig_kpi = px.bar(
    kpi_df[kpi_df['Year'].isin(selected_year)], 
    x="Quarter", y="RevPAR", color="Year", barmode="group",
    title="RevPAR Comparison by Quarter (2024-2026)",
    color_discrete_sequence=px.colors.qualitative.Pastel
)
st.plotly_chart(fig_kpi, use_container_width=True)

# -----------------------------
# Section 2: 2025 Gap Analysis
# -----------------------------
st.write("---")
st.header("2. 2025 ADR & RevPAR Gap Analysis")
st.error("Total Revenue Leakage in 2025: **-$265,545** primarily due to volume collapse in Q3.")

col_gap_1, col_gap_2 = st.columns([2, 1])

with col_gap_1:
    fig_loss = px.area(gap_df, x="Quarter", y="Rev_Loss", title="Revenue Loss Trends by Quarter (2025)")
    fig_loss.update_traces(line_color='#d9534f')
    st.plotly_chart(fig_loss, use_container_width=True)

with col_gap_2:
    st.write("#### Primary Leakage Causes")
    for _, row in gap_df.iterrows():
        st.markdown(f"**{row['Quarter']}**: {row['Cause']}  \n*(Loss: ${abs(row['Rev_Loss']):,.0f})*")

# -----------------------------
# Section 3: 2026 Strategy
# -----------------------------
st.write("---")
st.header("3. 2026 Strategic Recovery Plan")
st.info("Objective: Rebalance pricing to achieve 2024 baseline revenue levels.")

strat_1, strat_2 = st.columns(2)

with strat_1:
    st.markdown("""
    <div class="strategy-box">
        <h4>Immediate Pricing Adjustments (Next 48 Hours)</h4>
        <ul>
            <li><b>Lower Q2 Floor:</b> Drop rates by 10-18% across all OTAs.</li>
            <li><b>Target ADR:</b> Realign from $121 to ~$109 to drive 75%+ Occupancy.</li>
            <li><b>Spring Promotion:</b> Launch "Stay 2, Save 20%" via GDS/Web.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with strat_2:
    st.markdown("""
    <div class="strategy-box">
        <h4>Inventory & Channel Activation</h4>
        <ul>
            <li><b>Reactivate Rate Codes:</b> Recover SO2BK and SO2R (Lost $200K+ contribution).</li>
            <li><b>ChoiceMAX Audit:</b> Calibrate seasonal parameters to market demand.</li>
            <li><b>Distribution:</b> Optimize Wholesale and GDS presence.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Roadmap Table
st.write("#### Execution Roadmap")
roadmap = pd.DataFrame({
    "Timeframe": ["Next 48 Hours", "Next 48 Hours", "Next 48 Hours", "Next 72 Hours"],
    "Task": [
        "Lower Q2 floor rates by 10-18%",
        "Audit/Reactivate SO2BK & SO1R",
        "Launch 'Stay 2, Save 20%' Promo",
        "Finalize Q3/Q4 Distribution Strategy"
    ],
    "Stakeholder": ["Revenue Mgr", "Tech/Ops", "Marketing", "Leadership"]
})
st.table(roadmap)

st.success("Target Rebalance: ~\$109 ADR @ 75-80% Occ = Higher Total Revenue than Current \$121 ADR @ 25% Occ.")
