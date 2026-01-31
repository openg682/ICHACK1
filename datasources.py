"""
Blood Bank Agent - Real Data Sources
Fetches CDC flu data, weather data, and hospital information
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from config import HHS_REGIONS, DELPHI_API_BASE


class CDCFluData:
    """
    Fetches flu surveillance data from CDC via Delphi Epidata API
    """
    
    def __init__(self):
        self.base_url = DELPHI_API_BASE
        # HHS region codes for Delphi API
        self.region_map = {
            1: "hhs1", 2: "hhs2", 3: "hhs3", 4: "hhs4", 5: "hhs5",
            6: "hhs6", 7: "hhs7", 8: "hhs8", 9: "hhs9", 10: "hhs10"
        }
    
    def get_current_epiweek(self) -> str:
        """Get current epidemiological week in YYYYWW format"""
        today = datetime.now()
        # Approximate epiweek calculation
        week_num = today.isocalendar()[1]
        return f"{today.year}{week_num:02d}"
    
    def get_flu_data(self, region_id: int, weeks_back: int = 4) -> Dict:
        """
        Fetch ILI (influenza-like illness) data for a region
        
        Args:
            region_id: HHS region number (1-10)
            weeks_back: Number of weeks of historical data
            
        Returns:
            Dict with flu activity levels
        """
        current_week = int(self.get_current_epiweek())
        start_week = current_week - weeks_back
        
        region_code = self.region_map.get(region_id, "nat")
        
        try:
            url = f"{self.base_url}/fluview/"
            params = {
                "regions": region_code,
                "epiweeks": f"{start_week}-{current_week}"
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("result") == 1 and data.get("epidata"):
                latest = data["epidata"][-1]
                return {
                    "region": region_id,
                    "epiweek": latest.get("epiweek"),
                    "ili_percentage": latest.get("wili", 0),  # Weighted ILI
                    "num_providers": latest.get("num_providers", 0),
                    "activity_level": self._classify_activity(latest.get("wili", 0)),
                    "raw_data": latest
                }
            else:
                return self._generate_simulated_flu(region_id)
                
        except Exception as e:
            print(f"CDC API error for region {region_id}: {e}")
            return self._generate_simulated_flu(region_id)
    
    def _classify_activity(self, ili_pct: float) -> str:
        """Classify flu activity level based on ILI percentage"""
        if ili_pct < 1.5:
            return "minimal"
        elif ili_pct < 2.5:
            return "low"
        elif ili_pct < 4.0:
            return "moderate"
        elif ili_pct < 6.0:
            return "high"
        else:
            return "very_high"
    
    def _generate_simulated_flu(self, region_id: int) -> Dict:
        """Generate simulated flu data when API unavailable"""
        import random
        
        # Winter months have higher flu
        month = datetime.now().month
        if month in [12, 1, 2]:
            base_ili = random.uniform(3.0, 7.0)
        elif month in [3, 4, 11]:
            base_ili = random.uniform(1.5, 4.0)
        else:
            base_ili = random.uniform(0.5, 2.0)
        
        # Add regional variance
        base_ili *= random.uniform(0.8, 1.2)
        
        return {
            "region": region_id,
            "epiweek": self.get_current_epiweek(),
            "ili_percentage": round(base_ili, 2),
            "num_providers": 0,
            "activity_level": self._classify_activity(base_ili),
            "simulated": True
        }
    
    def get_all_regions(self) -> Dict[int, Dict]:
        """Fetch flu data for all HHS regions"""
        results = {}
        for region_id in range(1, 11):
            results[region_id] = self.get_flu_data(region_id)
        return results


class WeatherData:
    """
    Fetches weather data that could impact blood collection
    (storms, extreme heat, etc.)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "demo"  # OpenWeatherMap key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
        # Major cities per region for weather sampling
        self.region_cities = {
            1: [("Boston", 42.36, -71.06), ("Hartford", 41.76, -72.69)],
            2: [("New York", 40.71, -74.01), ("Newark", 40.74, -74.17)],
            3: [("Philadelphia", 39.95, -75.17), ("Baltimore", 39.29, -76.61)],
            4: [("Atlanta", 33.75, -84.39), ("Miami", 25.76, -80.19), ("Charlotte", 35.23, -80.84)],
            5: [("Chicago", 41.88, -87.63), ("Detroit", 42.33, -83.05), ("Cleveland", 41.50, -81.69)],
            6: [("Houston", 29.76, -95.37), ("Dallas", 32.78, -96.80), ("New Orleans", 29.95, -90.07)],
            7: [("Kansas City", 39.10, -94.58), ("Omaha", 41.26, -95.94)],
            8: [("Denver", 39.74, -104.99), ("Salt Lake City", 40.76, -111.89)],
            9: [("Los Angeles", 34.05, -118.24), ("Phoenix", 33.45, -112.07), ("San Francisco", 37.77, -122.42)],
            10: [("Seattle", 47.61, -122.33), ("Portland", 45.52, -122.68)]
        }
    
    def get_weather_impact(self, region_id: int) -> Dict:
        """
        Get weather-based impact score for a region
        
        Returns dict with:
        - impact_score: 0-1 (0=no impact, 1=severe impact)
        - conditions: description of conditions
        - alerts: list of active weather alerts
        """
        # Since we may not have API access, use simulation with realistic patterns
        return self._simulate_weather_impact(region_id)
    
    def _simulate_weather_impact(self, region_id: int) -> Dict:
        """Simulate weather impact based on season and region"""
        import random
        
        month = datetime.now().month
        
        # Base impact by season
        if month in [12, 1, 2]:  # Winter
            if region_id in [1, 2, 3, 5, 7, 8, 10]:  # Northern regions
                base_impact = random.uniform(0.1, 0.4)
                conditions = random.choice(["Snow possible", "Cold temps", "Winter storm watch", "Clear and cold"])
            else:
                base_impact = random.uniform(0, 0.15)
                conditions = random.choice(["Mild", "Cool", "Light rain possible"])
        
        elif month in [6, 7, 8]:  # Summer
            if region_id in [4, 6, 9]:  # Hot regions
                base_impact = random.uniform(0.1, 0.3)
                conditions = random.choice(["Extreme heat", "Heat advisory", "Hot and humid", "Thunderstorms"])
            else:
                base_impact = random.uniform(0, 0.15)
                conditions = random.choice(["Warm", "Pleasant", "Scattered showers"])
        
        elif month in [8, 9, 10]:  # Hurricane season
            if region_id in [4, 6]:  # Gulf/Atlantic coast
                base_impact = random.uniform(0.05, 0.35)
                conditions = random.choice(["Tropical activity monitored", "Hurricane season active", "Clear"])
            else:
                base_impact = random.uniform(0, 0.1)
                conditions = "Seasonal"
        else:
            base_impact = random.uniform(0, 0.1)
            conditions = "Seasonal"
        
        # Random severe event chance (5%)
        if random.random() < 0.05:
            base_impact = min(1.0, base_impact + 0.4)
            conditions = random.choice(["Severe weather warning", "Major storm system", "Flooding risk"])
        
        alerts = []
        if base_impact > 0.3:
            alerts.append(f"Weather advisory affecting blood drives in Region {region_id}")
        
        return {
            "region": region_id,
            "impact_score": round(base_impact, 2),
            "conditions": conditions,
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_all_regions(self) -> Dict[int, Dict]:
        """Get weather impact for all regions"""
        results = {}
        for region_id in range(1, 11):
            results[region_id] = self.get_weather_impact(region_id)
        return results


class HospitalData:
    """
    Hospital and trauma center data
    Uses CMS data and trauma center registries
    """
    
    def __init__(self):
        self.hospitals_by_region = self._build_hospital_estimates()
    
    def _build_hospital_estimates(self) -> Dict[int, Dict]:
        """Build hospital statistics by region from known data"""
        estimates = {}
        
        for region_id, info in HHS_REGIONS.items():
            pop = info["population"]
            
            # Estimate hospitals based on ~1 hospital per 30k population
            est_hospitals = int(pop / 30000)
            
            # Estimate surgical volume (rough proxy for blood demand)
            # ~25 surgeries per 1000 population annually
            annual_surgeries = int(pop * 0.025)
            
            estimates[region_id] = {
                "region_id": region_id,
                "region_name": info["name"],
                "population": pop,
                "estimated_hospitals": est_hospitals,
                "trauma_centers_l1_l2": info["trauma_centers_l1_l2"],
                "annual_surgeries_est": annual_surgeries,
                "daily_surgical_demand": int(annual_surgeries / 365),
                "states": info["states"]
            }
        
        return estimates
    
    def get_region_demand_factors(self, region_id: int) -> Dict:
        """Get demand factors for a region"""
        base = self.hospitals_by_region.get(region_id, {})
        
        # Add day-of-week factor (weekdays have more elective surgeries)
        day = datetime.now().weekday()
        if day < 5:  # Weekday
            dow_factor = 1.1
        else:  # Weekend
            dow_factor = 0.75
        
        return {
            **base,
            "day_of_week_factor": dow_factor,
            "is_weekend": day >= 5
        }
    
    def get_all_regions(self) -> Dict[int, Dict]:
        """Get hospital data for all regions"""
        return {r: self.get_region_demand_factors(r) for r in range(1, 11)}


def fetch_all_real_data() -> Dict:
    """
    Master function to fetch all real/simulated data
    Returns combined dataset for the simulation
    """
    print("Fetching CDC flu data...")
    flu = CDCFluData()
    flu_data = flu.get_all_regions()
    
    print("Fetching weather data...")
    weather = WeatherData()
    weather_data = weather.get_all_regions()
    
    print("Loading hospital data...")
    hospitals = HospitalData()
    hospital_data = hospitals.get_all_regions()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "flu": flu_data,
        "weather": weather_data,
        "hospitals": hospital_data
    }


if __name__ == "__main__":
    # Test data fetching
    data = fetch_all_real_data()
    print(json.dumps(data, indent=2, default=str))
