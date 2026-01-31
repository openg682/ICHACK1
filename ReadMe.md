# 🩸 Blood Bank Autonomous Agent

An AI-powered system for managing regional blood supply allocation across the United States. The agent monitors supply levels, analyzes external factors (flu outbreaks, weather), and autonomously makes decisions about shortage appeals, inter-regional transfers, and collection priorities.

## 🎯 Features

- **Real-time Data Integration**
  - CDC flu surveillance data via Delphi Epidata API
  - Weather impact modeling
  - Blood center news scraping for shortage alerts

- **Regional Simulation**
  - 10 HHS regions with realistic blood inventory
  - Blood type-specific tracking (O+, O-, A+, A-, B+, B-, AB+, AB-)
  - Shelf life management and expiration modeling
  - Seasonal and day-of-week demand patterns

- **Autonomous Agent**
  - Issue public shortage appeals
  - Recommend inter-regional blood transfers
  - Suggest elective surgery postponements
  - Prioritize collection efforts based on conditions

- **Interactive Dashboard**
  - Real-time supply heatmaps
  - Agent decision visualization
  - Regional drill-down analysis

## 🚀 Quick Start

### Installation

```bash
# Clone or copy the project
cd blood_bank_agent

# Install dependencies
pip install -r requirements.txt
```

### Run Demo

```bash
# Quick demo showing agent decisions
python main.py demo

# Full demonstration with all components
python main.py full

# Launch interactive dashboard
python main.py dashboard
```

## 📁 Project Structure

```
blood_bank_agent/
├── config.py           # Configuration, constants, thresholds
├── data_sources.py     # CDC flu API, weather, hospital data
├── scraper.py          # Blood center news scraping
├── simulation.py       # Regional blood supply simulation
├── agent.py            # Autonomous decision-making logic
├── dashboard.py        # Streamlit visualization
├── main.py             # Entry point / CLI
├── requirements.txt    # Dependencies
└── README.md           # This file
```

## 🔧 Components

### Data Sources (`data_sources.py`)

Fetches real-world data to inform the simulation:

- **CDC Flu Data**: Weekly ILI (influenza-like illness) rates by HHS region
- **Weather Impact**: Storm/heat wave modeling that affects blood collection
- **Hospital Data**: Trauma center distribution, surgical volumes

### Scraper (`scraper.py`)

Monitors blood center websites for shortage announcements:

- American Red Cross press releases
- Regional blood center news (NY Blood Center, OneBlood, Vitalant, etc.)
- Extracts severity levels, affected blood types, and geographic scope

### Simulation (`simulation.py`)

Models blood inventory dynamics:

```python
# Key classes
RegionalBloodBank       # Single region's inventory
NationalBloodSimulation # Coordinates all 10 regions

# Simulates daily:
- Blood collections (modified by flu/weather)
- Transfusions/demand
- Expiration of old units
- Inter-regional transfers
```

### Agent (`agent.py`)

Makes autonomous decisions based on supply state:

```python
# Action types
ISSUE_SHORTAGE_APPEAL           # Public donation request
TRANSFER_BLOOD                  # Inter-regional redistribution
RECOMMEND_ELECTIVE_POSTPONEMENT # Delay non-critical surgeries
INCREASE_COLLECTION_EFFORT      # Boost donor outreach
ALERT_CRITICAL                  # Immediate intervention needed
```

## 📊 Data Reality Check

| Data Type | Source | Availability |
|-----------|--------|--------------|
| Flu activity by region | CDC Delphi API | ✅ Real, free |
| Weather conditions | OpenWeatherMap / NWS | ✅ Real, free |
| Hospital locations | CMS Provider Data | ✅ Real, free |
| Trauma centers | ACS / Wikipedia | ✅ Real, free |
| **Blood inventory** | AABB (national only) | ⚠️ National aggregate only |
| **Regional inventory** | Individual blood centers | ❌ Not public |

The simulation generates **realistic regional supply levels** based on population, hospital distribution, and external factors, since actual regional inventory data is not publicly available.

## 🎮 Usage Examples

### Run Simulation

```python
from simulation import NationalBloodSimulation
from data_sources import fetch_all_real_data

# Initialize
sim = NationalBloodSimulation()
data = fetch_all_real_data()

# Simulate 7 days
for _ in range(7):
    result = sim.simulate_day(external_data=data)
    print(f"National supply: {result['national']['overall_days_of_supply']:.1f} days")
```

### Get Agent Recommendations

```python
from agent import BloodBankAgent

agent = BloodBankAgent(sim)
actions = agent.analyze_and_act()

for action in actions:
    print(f"{action.priority}: {action.action_type.value}")
    print(f"  {action.reasoning}")
```

### Inject Crisis Event

```python
# Mass casualty event in Region 4 (Southeast)
events = [{
    "type": "mass_casualty",
    "region_id": 4,
    "severity": 2.5  # 2.5x normal demand
}]

result = sim.simulate_day(external_data=data, events=events)
```

## 🔮 Extending the Project

### Add Real Weather API

```python
# In data_sources.py, add your OpenWeatherMap key:
weather = WeatherData(api_key="your-key-here")
```

### Customize Agent Thresholds

```python
# In config.py:
AGENT_THRESHOLDS = {
    "issue_appeal": 1.5,      # Days of supply
    "transfer_trigger": 1.0,   # Days difference
    "postpone_elective": 0.75  # Critical threshold
}
```

### Add New Blood Centers to Scraper

```python
# In scraper.py, add to self.sources:
"new_center": {
    "url": "https://example.org/news",
    "region": 5,
    "parser": self._parse_generic_news
}
```

## 📈 Demo Scenarios

The project includes several pre-built scenarios:

1. **Winter Flu Season**: High flu activity reduces donations
2. **Hurricane Impact**: Weather disrupts Gulf Coast collections
3. **Mass Casualty Event**: Sudden spike in demand in one region
4. **Holiday Period**: Reduced donations, lower elective surgery

## 🏆 For Hackathons

This project is designed to be presentable in 24 hours:

1. **Core demo** (2 hours): Run `python main.py demo`
2. **Dashboard** (add 3 hours): `python main.py dashboard`
3. **Custom scenarios** (add 2 hours): Modify events in `main.py`
4. **Pitch deck integration**: Export charts from dashboard

## 📝 License

MIT License - feel free to use for hackathons, learning, or production.

## 🙏 Acknowledgments

- CDC Delphi Group for the Epidata API
- AABB for blood supply reporting methodology
- America's Blood Centers member directory
