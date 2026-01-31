"""
Blood Bank Agent - Streamlit Dashboard
Interactive visualization of the blood supply simulation and agent decisions
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json

from config import HHS_REGIONS, BLOOD_TYPE_DISTRIBUTION
from simulation import NationalBloodSimulation
from agent import BloodBankAgent, ActionType
from data_sources import fetch_all_real_data
from scraper import get_shortage_intelligence


# Page config
st.set_page_config(
    page_title="Blood Bank Agent",
    page_icon="🩸",
    layout="wide"
)


@st.cache_resource
def initialize_simulation():
    """Initialize and cache the simulation"""
    sim = NationalBloodSimulation()
    return sim


@st.cache_data(ttl=3600)
def fetch_external_data():
    """Fetch and cache external data"""
    return fetch_all_real_data()


@st.cache_data(ttl=3600)  
def fetch_shortage_data():
    """Fetch shortage intelligence"""
    return get_shortage_intelligence()


def create_supply_heatmap(state: dict) -> go.Figure:
    """Create a heatmap of blood supply by region and type"""
    data = []
    
    regions = list(state.keys())
    blood_types = list(BLOOD_TYPE_DISTRIBUTION.keys())
    
    for region_id in regions:
        row = []
        for bt in blood_types:
            dos = state[region_id]["inventory"].get(bt, {}).get("days_of_supply", 0)
            row.append(dos)
        data.append(row)
    
    region_names = [HHS_REGIONS[r]["name"].replace("Region ", "").split(" - ")[1] 
                   if " - " in HHS_REGIONS[r]["name"] else f"R{r}" 
                   for r in regions]
    
    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=blood_types,
        y=region_names,
        colorscale=[
            [0, 'red'],
            [0.25, 'orange'],
            [0.5, 'yellow'],
            [0.75, 'lightgreen'],
            [1, 'green']
        ],
        zmin=0,
        zmax=5,
        colorbar=dict(title="Days of Supply"),
        text=[[f"{v:.1f}" for v in row] for row in data],
        texttemplate="%{text}",
        textfont={"size": 10}
    ))
    
    fig.update_layout(
        title="Blood Supply by Region and Type (Days of Supply)",
        xaxis_title="Blood Type",
        yaxis_title="Region",
        height=500
    )
    
    return fig


def create_regional_bar_chart(state: dict) -> go.Figure:
    """Create bar chart of overall supply by region"""
    regions = []
    dos_values = []
    colors = []
    
    for region_id, data in state.items():
        regions.append(HHS_REGIONS[region_id]["name"].split(" - ")[-1])
        dos = data["overall_days_of_supply"]
        dos_values.append(dos)
        
        if dos < 1:
            colors.append('red')
        elif dos < 2:
            colors.append('orange')
        elif dos < 3:
            colors.append('yellow')
        else:
            colors.append('green')
    
    fig = go.Figure(data=[
        go.Bar(
            x=regions,
            y=dos_values,
            marker_color=colors,
            text=[f"{v:.1f}" for v in dos_values],
            textposition='outside'
        )
    ])
    
    fig.add_hline(y=3, line_dash="dash", line_color="green", 
                  annotation_text="Target: 3 days")
    fig.add_hline(y=1.5, line_dash="dash", line_color="orange",
                  annotation_text="Warning: 1.5 days")
    
    fig.update_layout(
        title="Overall Days of Supply by Region",
        xaxis_title="Region",
        yaxis_title="Days of Supply",
        height=400
    )
    
    return fig


def render_action_card(action, index: int):
    """Render a single action as a card"""
    priority_colors = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢"
    }
    
    icon = priority_colors.get(action.priority, "⚪")
    
    with st.expander(f"{icon} {action.action_type.value.replace('_', ' ').title()} - {action.priority.upper()}", expanded=(index < 3)):
        
        if action.region_id:
            st.write(f"**Region:** {HHS_REGIONS[action.region_id]['name']}")
        else:
            st.write("**Scope:** National")
        
        st.write(f"**Blood Types:** {', '.join(action.blood_types)}")
        
        st.markdown("---")
        st.write("**Reasoning:**")
        st.info(action.reasoning)
        
        if action.details.get("suggested_messaging"):
            st.write("**Suggested Public Message:**")
            st.success(action.details["suggested_messaging"])
        
        if action.details.get("units_needed"):
            st.write("**Units Needed:**")
            cols = st.columns(4)
            for i, (bt, units) in enumerate(action.details["units_needed"].items()):
                cols[i % 4].metric(bt, f"{units} units")
        
        if action.details.get("suggested_actions"):
            st.write("**Recommended Steps:**")
            for step in action.details["suggested_actions"]:
                st.write(f"• {step}")


def main():
    st.title("🩸 Blood Bank Autonomous Agent")
    st.markdown("*Real-time blood supply monitoring and intelligent allocation*")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Controls")
        
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        st.header("📊 Simulation")
        sim_days = st.slider("Days to simulate", 1, 14, 7)
        
        if st.button("▶️ Run Simulation"):
            st.session_state.run_sim = True
        
        st.markdown("---")
        
        st.header("ℹ️ About")
        st.markdown("""
        This dashboard demonstrates an autonomous AI agent
        managing blood bank inventory across US regions.
        
        **Data Sources:**
        - CDC Flu Surveillance (Delphi API)
        - Weather impact modeling
        - Blood center news scraping
        
        **Agent Actions:**
        - Issue shortage appeals
        - Recommend transfers
        - Postpone electives
        - Increase collection efforts
        """)
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Dashboard", "🤖 Agent Actions", "📰 Intelligence", "📋 Details"])
    
    # Initialize
    sim = initialize_simulation()
    external_data = fetch_external_data()
    
    # Run simulation if requested
    if st.session_state.get('run_sim', False) or 'sim_result' not in st.session_state:
        with st.spinner("Running simulation..."):
            for _ in range(sim_days):
                sim.simulate_day(external_data=external_data)
            st.session_state.sim_result = sim.get_current_state()
            st.session_state.run_sim = False
    
    state = st.session_state.sim_result
    
    with tab1:
        # Key metrics
        st.header("National Blood Supply Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate national metrics
        avg_dos = sum(s["overall_days_of_supply"] for s in state.values()) / len(state)
        critical_regions = sum(1 for s in state.values() if s["status"] == "critical")
        low_regions = sum(1 for s in state.values() if s["status"] == "low")
        
        col1.metric("National Avg Supply", f"{avg_dos:.1f} days", 
                   delta=None if avg_dos > 2.5 else "Low")
        col2.metric("Critical Regions", critical_regions, 
                   delta=None if critical_regions == 0 else "Alert")
        col3.metric("Low Supply Regions", low_regions)
        col4.metric("Adequate Regions", 10 - critical_regions - low_regions)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            fig = create_regional_bar_chart(state)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = create_supply_heatmap(state)
            st.plotly_chart(fig, use_container_width=True)
        
        # Critical alerts
        critical_types = set()
        for region_state in state.values():
            for bt, inv in region_state["inventory"].items():
                if inv["days_of_supply"] < 1.5:
                    critical_types.add(bt)
        
        if critical_types:
            st.error(f"⚠️ **Critical blood types nationally:** {', '.join(critical_types)}")
    
    with tab2:
        st.header("🤖 Agent Decisions")
        
        # Initialize and run agent
        agent = BloodBankAgent(sim)
        actions = agent.analyze_and_act(external_context=external_data)
        
        if not actions:
            st.success("✅ No immediate actions required. Blood supply is stable.")
        else:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            
            critical_actions = sum(1 for a in actions if a.priority == "critical")
            high_actions = sum(1 for a in actions if a.priority == "high")
            
            col1.metric("Total Actions", len(actions))
            col2.metric("Critical Priority", critical_actions)
            col3.metric("High Priority", high_actions)
            
            st.markdown("---")
            
            # Filter
            priority_filter = st.multiselect(
                "Filter by priority",
                ["critical", "high", "medium", "low"],
                default=["critical", "high"]
            )
            
            filtered_actions = [a for a in actions if a.priority in priority_filter]
            
            # Display actions
            for i, action in enumerate(filtered_actions):
                render_action_card(action, i)
    
    with tab3:
        st.header("📰 Shortage Intelligence")
        
        with st.spinner("Gathering intelligence..."):
            intel = fetch_shortage_data()
        
        # Scraped alerts
        st.subheader("News Alerts")
        if intel.get("scraped_alerts"):
            for alert in intel["scraped_alerts"]:
                severity_emoji = {"critical": "🔴", "severe": "🟠", "moderate": "🟡"}.get(alert.get("severity"), "⚪")
                st.write(f"{severity_emoji} **{alert.get('source')}**: {alert.get('headline', 'No headline')}")
                st.caption(f"Blood types: {', '.join(alert.get('blood_types', []))}")
        else:
            st.info("No recent shortage alerts detected from news sources.")
        
        st.markdown("---")
        
        # Regional status from scraping
        st.subheader("Regional Status (Intelligence)")
        
        regional_status = intel.get("regional_status", {})
        
        cols = st.columns(5)
        for i, (region_id, status) in enumerate(regional_status.items()):
            col = cols[i % 5]
            
            if status.get("has_shortage"):
                icon = "🔴" if status["severity"] == "critical" else "🟠"
            else:
                icon = "🟢"
            
            col.metric(
                f"R{region_id}",
                f"{status.get('days_of_supply', 0):.1f}d",
                delta=status.get("severity", "adequate")
            )
    
    with tab4:
        st.header("📋 Detailed Regional Data")
        
        selected_region = st.selectbox(
            "Select Region",
            options=list(state.keys()),
            format_func=lambda x: HHS_REGIONS[x]["name"]
        )
        
        if selected_region:
            region_data = state[selected_region]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Overview")
                st.metric("Overall Supply", f"{region_data['overall_days_of_supply']:.1f} days")
                st.metric("Status", region_data["status"].upper())
                st.metric("Min Supply", f"{region_data['min_days_of_supply']:.1f} days")
            
            with col2:
                st.subheader("Impact Factors")
                flu = region_data.get("modifiers", {}).get("flu_impact", 0)
                weather = region_data.get("modifiers", {}).get("weather_impact", 0)
                st.progress(flu, text=f"Flu Impact: {flu:.0%}")
                st.progress(weather, text=f"Weather Impact: {weather:.0%}")
            
            st.subheader("Inventory by Blood Type")
            
            inv_data = []
            for bt, inv in region_data["inventory"].items():
                inv_data.append({
                    "Blood Type": bt,
                    "Units": inv["units"],
                    "Days of Supply": inv["days_of_supply"],
                    "Status": inv["status"]
                })
            
            df = pd.DataFrame(inv_data)
            
            # Color code the dataframe
            def color_status(val):
                if val == "critical":
                    return "background-color: #ff4444"
                elif val == "low":
                    return "background-color: #ffaa00"
                elif val == "adequate":
                    return "background-color: #ffff00"
                else:
                    return "background-color: #44ff44"
            
            styled_df = df.style.applymap(color_status, subset=["Status"])
            st.dataframe(styled_df, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data sources: CDC, Weather APIs, Blood Center News")


if __name__ == "__main__":
    main()
