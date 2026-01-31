#!/usr/bin/env python3
"""
Blood Bank Agent - Main Entry Point

Usage:
    python main.py demo          Run a quick demo of the agent
    python main.py simulate N    Run N days of simulation
    python main.py dashboard     Launch the Streamlit dashboard
    python main.py scrape        Test the news scraper
    python main.py full          Run full demo with all components
"""

import sys
import json
from datetime import datetime


def run_demo():
    """Run a quick demonstration"""
    print("\n" + "=" * 70)
    print("🩸 BLOOD BANK AUTONOMOUS AGENT - DEMO")
    print("=" * 70)
    
    from simulation import NationalBloodSimulation
    from agent import BloodBankAgent
    from data_sources import fetch_all_real_data
    
    # Initialize
    print("\n📊 Initializing simulation...")
    sim = NationalBloodSimulation()
    
    print("🌐 Fetching real-world data...")
    external_data = fetch_all_real_data()
    
    # Simulate 5 days
    print("⏱️  Running 5-day simulation...")
    for day in range(5):
        events = []
        if day == 3:  # Add a crisis on day 3
            events.append({
                "type": "mass_casualty",
                "region_id": 4,
                "severity": 2.0
            })
            print(f"  Day {day+1}: 🚨 Mass casualty event in Southeast region!")
        else:
            print(f"  Day {day+1}: Normal operations")
        
        sim.simulate_day(external_data=external_data, events=events)
    
    # Get agent decisions
    print("\n🤖 Agent analyzing situation...")
    agent = BloodBankAgent(sim)
    actions = agent.analyze_and_act()
    
    # Display results
    print("\n" + "=" * 70)
    print(f"📋 AGENT GENERATED {len(actions)} ACTIONS")
    print("=" * 70)
    
    for i, action in enumerate(actions[:5], 1):  # Show top 5
        priority_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        icon = priority_icons.get(action.priority, "⚪")
        
        print(f"\n{icon} Action {i}: {action.action_type.value.replace('_', ' ').title()}")
        print(f"   Priority: {action.priority.upper()}")
        if action.region_id:
            from config import HHS_REGIONS
            print(f"   Region: {HHS_REGIONS[action.region_id]['name']}")
        print(f"   Blood Types: {', '.join(action.blood_types)}")
        print(f"   Reasoning: {action.reasoning[:200]}...")
    
    print("\n" + "=" * 70)
    print("✅ Demo complete!")
    print("=" * 70)


def run_simulation(days: int):
    """Run simulation for specified days"""
    from simulation import run_simulation_demo
    
    print(f"\n🩸 Running {days}-day blood bank simulation...")
    result = run_simulation_demo(days=days)
    
    print("\n📊 Final State Summary:")
    for region_id, data in result["final_state"].items():
        status_icon = "🔴" if data["status"] == "critical" else "🟡" if data["status"] == "low" else "🟢"
        print(f"  {status_icon} Region {region_id}: {data['overall_days_of_supply']:.1f} days supply")
    
    if result["transfer_recommendations"]:
        print("\n🔄 Transfer Recommendations:")
        for rec in result["transfer_recommendations"][:3]:
            print(f"  • Transfer {rec['units_recommended']} units {rec['blood_type']} "
                  f"from Region {rec['from_region']} → Region {rec['to_region']}")


def run_dashboard():
    """Launch the Streamlit dashboard"""
    import subprocess
    print("\n🚀 Launching Blood Bank Agent Dashboard...")
    print("   Open http://localhost:8501 in your browser")
    print("   Press Ctrl+C to stop\n")
    subprocess.run(["streamlit", "run", "dashboard.py"])


def run_scraper():
    """Test the news scraper"""
    from scraper import get_shortage_intelligence
    
    print("\n📰 Testing Blood Center News Scraper...")
    intel = get_shortage_intelligence()
    
    print(f"\nScraped Alerts: {len(intel.get('scraped_alerts', []))}")
    for alert in intel.get("scraped_alerts", [])[:5]:
        print(f"  • {alert['source']}: {alert.get('headline', 'N/A')[:60]}...")
    
    print(f"\nRegional Status:")
    for region_id, status in intel.get("regional_status", {}).items():
        icon = "🔴" if status.get("has_shortage") else "🟢"
        print(f"  {icon} Region {region_id}: {status.get('severity', 'adequate')} - "
              f"{status.get('days_of_supply', 0):.1f} days")


def run_full():
    """Run full demonstration with all components"""
    print("\n" + "=" * 70)
    print("🩸 BLOOD BANK AGENT - FULL DEMONSTRATION")
    print("=" * 70)
    
    # 1. Fetch data
    print("\n[1/4] 🌐 Fetching External Data...")
    from data_sources import fetch_all_real_data
    external_data = fetch_all_real_data()
    
    print(f"  ✓ Flu data for {len(external_data['flu'])} regions")
    print(f"  ✓ Weather data for {len(external_data['weather'])} regions")
    print(f"  ✓ Hospital data for {len(external_data['hospitals'])} regions")
    
    # 2. Scrape intelligence
    print("\n[2/4] 📰 Gathering Shortage Intelligence...")
    from scraper import get_shortage_intelligence
    intel = get_shortage_intelligence()
    
    alerts = intel.get("scraped_alerts", [])
    print(f"  ✓ Found {len(alerts)} news alerts")
    
    shortage_regions = [r for r, s in intel.get("regional_status", {}).items() 
                       if s.get("has_shortage")]
    print(f"  ✓ {len(shortage_regions)} regions with detected shortages")
    
    # 3. Run simulation
    print("\n[3/4] ⏱️  Running 7-Day Simulation...")
    from simulation import NationalBloodSimulation
    sim = NationalBloodSimulation()
    
    for day in range(7):
        events = []
        # Inject realistic events
        if day == 2:
            events.append({"type": "mass_casualty", "region_id": 2, "severity": 1.8})
            print(f"    Day {day+1}: 🚨 Major incident in NY region")
        elif day == 5:
            events.append({"type": "holiday", "region_id": None, "severity": 0.8})
            print(f"    Day {day+1}: 🎄 Holiday - reduced collections expected")
        else:
            print(f"    Day {day+1}: Normal operations")
        
        sim.simulate_day(external_data=external_data, events=events)
    
    # 4. Agent analysis
    print("\n[4/4] 🤖 Agent Analysis & Decisions...")
    from agent import BloodBankAgent
    agent = BloodBankAgent(sim)
    actions = agent.analyze_and_act(external_context=external_data)
    
    # Results
    print("\n" + "=" * 70)
    print("📊 SIMULATION RESULTS")
    print("=" * 70)
    
    state = sim.get_current_state()
    
    print("\nRegional Supply Status:")
    for region_id, data in state.items():
        from config import HHS_REGIONS
        status_icons = {"critical": "🔴", "low": "🟡", "adequate": "🟢"}
        icon = status_icons.get(data["status"], "⚪")
        name = HHS_REGIONS[region_id]["name"].split(" - ")[-1]
        print(f"  {icon} {name}: {data['overall_days_of_supply']:.1f} days "
              f"(min: {data['min_days_of_supply']:.1f})")
    
    print("\n" + "=" * 70)
    print(f"🤖 AGENT ACTIONS ({len(actions)} total)")
    print("=" * 70)
    
    # Group by priority
    by_priority = {}
    for action in actions:
        p = action.priority
        by_priority[p] = by_priority.get(p, []) + [action]
    
    for priority in ["critical", "high", "medium", "low"]:
        if priority in by_priority:
            print(f"\n{'🔴' if priority == 'critical' else '🟠' if priority == 'high' else '🟡' if priority == 'medium' else '🟢'} {priority.upper()} PRIORITY ({len(by_priority[priority])} actions):")
            for action in by_priority[priority][:3]:
                from config import HHS_REGIONS
                region_name = HHS_REGIONS[action.region_id]["name"] if action.region_id else "National"
                print(f"    • {action.action_type.value.replace('_', ' ').title()}")
                print(f"      Region: {region_name}")
                print(f"      Reasoning: {action.reasoning[:100]}...")
    
    print("\n" + "=" * 70)
    print("✅ Full demonstration complete!")
    print("\nNext steps:")
    print("  1. Run 'python main.py dashboard' to launch interactive UI")
    print("  2. Modify simulation parameters in config.py")
    print("  3. Add real API keys for weather data")
    print("=" * 70)


def print_usage():
    """Print usage information"""
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "demo":
        run_demo()
    elif command == "simulate":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        run_simulation(days)
    elif command == "dashboard":
        run_dashboard()
    elif command == "scrape":
        run_scraper()
    elif command == "full":
        run_full()
    else:
        print(f"Unknown command: {command}")
        print_usage()


if __name__ == "__main__":
    main()
