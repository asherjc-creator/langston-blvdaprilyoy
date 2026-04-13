import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="Revenue Recovery Portal | 2026 Strategy",
    layout="wide",
    page_icon="📈"
)

# -----------------------------
# Data Loading (Updated with User Tables & PDF Source)
# -----------------------------
@st.cache_data
def load_dashboard_data():
    # 1. 3-Year KPI Comparison (Derived from [cite: 9])
    kpi_comp = pd.DataFrame([
        {"Year": 2024, "ADR": 109.68, "RevPAR": 121.22, "OCC%": 90.5, "Rooms_Revenue": 485000},
        {"Year": 2025, "ADR": 97.57, "RevPAR": 109.19, "OCC%": 89.4, "Rooms_Revenue": 412000},
        {"Year": 2026, "ADR": 121.55, "RevPAR": 30.95, "OCC%": 25.5, "Rooms_Revenue": 115000}
    ])

    # 2. Graphical Rate Code Performance (User Requested Table)
    rate_code_data = pd.DataFrame([
        {"Rate Code": "SO2BK", "2024 Revenue": 60631, "Status 2025": "Performing", "Status 2026": "Disappeared"},
        {"Rate Code": "SO1R", "2024 Revenue": 35596, "Status 2025": "Disappeared", "Status 2026": "Disappeared"},
        {"Rate Code": "SOPM1M", "2024 Revenue": 34228, "Status 2025": "Disappeared", "Status 2026": "Disappeared"},
        {"Rate Code": "SO2R", "2024 Revenue": 29754, "Status 2025": "Performing", "Status 2026": "Disappeared"},
        {"Rate Code": "SO1EXP", "2024 Revenue": 27177, "Status 2025": "Disappeared", "Status 2026": "Disappeared"},
        {"Rate Code": "GROUP", "2024 Revenue": 22739, "Status 2025": "Underperforming", "Status 2026": "Disappeared"}
    ])
    
    return kpi_comp, rate_code_data

kpi_df, rate_df = load_dashboard_data()

# -----------------------------
# Header Section
# -----------------------------
st.title("🏨 2026 Revenue Recovery & Strategy Portal")
st.info("Strategic Focus: Reclaiming >$200K in lost segment contribution by rebalancing pricing and volume[cite: 22, 37].")

# -----------------------------
# Section 1: Dashboard KPI Comparison (2024-2026)
# -----------------------------
st.header("1. 3-Year KPI Comparison (Q2 Performance)")
cols = st.columns(4)

# Displaying Metrics for the latest year (2026) with comparison to 2024 baseline
for i, metric in enumerate(["ADR", "RevPAR", "OCC%", "Rooms_Revenue"]):
    val_26 = kpi_df.loc[2, metric]
    val_24 = kpi_df.loc[0, metric]
    delta = val_26 - val_24
    
    suffix = "$" if metric != "OCC%" else "%"
    prefix = "$" if metric in ["ADR", "RevPAR", "Rooms_Revenue"] else ""
    
    cols[i].metric(
        label=metric.replace("_", " "),
        value=f"{prefix}{val_26:,.2f}{suffix if metric == 'OCC%' else ''}",
        delta=f"{delta:,.2f} vs 2024",
        delta_color="inverse" if metric != "ADR" else "normal"
    )

# Visual Comparison Chart
fig_kpi = go.Figure()
for metric in ["ADR", "RevPAR"]:
    fig_kpi.add_trace(go.Bar(x=kpi_df["Year"], y=kpi_df[metric], name=metric))

fig_kpi.update_layout(title="ADR vs RevPAR Trends (2024-2026)", barmode='group', height=400)
st.plotly_chart(fig_kpi, use_container_width=True)

# -----------------------------
# Section 2: Rate Code Performance (Graphical Table)
# -----------------------------
st.write("---")
st.header("2. Critical Rate Code Analysis (Revenue Leakage)")

def style_status(val):
    if val == "Disappeared": return 'color: #d9534f; font-weight: bold'
    if val == "Performing": return 'color: #5cb85c; font-weight: bold'
    return 'color: #f0ad4e'

styled_rate_df = rate_df.style.applymap(style_status, subset=['Status 2025', 'Status 2026'])\
    .format({"2024 Revenue": "${:,.0f}"})

st.table(styled_rate_df)

# Graphical Breakdown of Lost Revenue
fig_rate = px.pie(rate_df, values='2024 Revenue', names='Rate Code', 
                 title="2024 Contribution of Now-Inactive Segments",
                 hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
st.plotly_chart(fig_rate, use_container_width=True)

# -----------------------------
# Section 3: Strategic Recovery Plan (0-7 Days)
# -----------------------------
st.write("---")
st.header("3. 0-7 Day Execution Roadmap")

roadmap_data = pd.DataFrame({
    "Day Range": ["Day 0-2", "Day 0-2", "Day 0-2", "Day 3-5", "Day 5-7"],
    "Priority Task": [
        "Immediate Rate Drop: Lower Q2 floor by 10-18% ",
        "Audit Inactive Codes: Investigate SO2BK, SO1R, & SO2R ",
        "Launch 'Stay 2, Save 20%' Spring Promo ",
        "Reactivate High-Producing Rate Codes in PMS/CRS [cite: 36]",
        "Leadership Review: Q3/Q4 Distribution Strategy "
    ],
    "Owner": ["Revenue Mgr", "Tech/Ops", "Marketing", "Leadership"],
    "Status": ["Urgent", "Urgent", "In Progress", "Planned", "Scheduled"]
})

# Displaying the roadmap with status coloring
st.table(roadmap_data)

st.warning("**Note:** Target rebalance is ~$109 ADR at 75-80% Occupancy to recover lost RevPAR[cite: 42].")
