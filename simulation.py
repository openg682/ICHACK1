"""
Blood Bank Agent - Regional Blood Supply Simulation
Simulates realistic blood inventory levels based on real-world factors
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
import math

from config import (
    HHS_REGIONS, 
    BLOOD_TYPE_DISTRIBUTION,
    SHELF_LIFE,
    BASE_DEMAND_PER_100K,
    SEASONAL_FACTORS,
    SUPPLY_STATUS
)


@dataclass
class BloodInventory:
    """Represents blood inventory for a single blood type"""
    blood_type: str
    units_available: int
    units_by_age: Dict[int, int] = field(default_factory=dict)  # age_days -> count
    daily_demand: float = 0.0
    days_of_supply: float = 0.0
    
    def calculate_days_of_supply(self) -> float:
        """Calculate days of supply based on current inventory and demand"""
        if self.daily_demand > 0:
            self.days_of_supply = self.units_available / self.daily_demand
        else:
            self.days_of_supply = float('inf')
        return self.days_of_supply
    
    def age_inventory(self):
        """Age all inventory by one day, removing expired units"""
        new_by_age = {}
        expired = 0
        
        for age, count in self.units_by_age.items():
            new_age = age + 1
            if new_age >= SHELF_LIFE.get("RBC", 42):
                expired += count
            else:
                new_by_age[new_age] = count
        
        self.units_by_age = new_by_age
        self.units_available = sum(new_by_age.values())
        
        return expired
    
    def add_units(self, count: int, age: int = 0):
        """Add new units to inventory"""
        self.units_by_age[age] = self.units_by_age.get(age, 0) + count
        self.units_available += count
    
    def remove_units(self, count: int) -> int:
        """Remove units (use oldest first). Returns actual units removed."""
        removed = 0
        
        # Sort by age descending (use oldest first)
        for age in sorted(self.units_by_age.keys(), reverse=True):
            if removed >= count:
                break
            
            available = self.units_by_age[age]
            to_remove = min(available, count - removed)
            
            self.units_by_age[age] -= to_remove
            if self.units_by_age[age] == 0:
                del self.units_by_age[age]
            
            removed += to_remove
        
        self.units_available -= removed
        return removed


@dataclass
class RegionalBloodBank:
    """Represents a regional blood bank with full inventory"""
    region_id: int
    region_name: str
    population: int
    inventory: Dict[str, BloodInventory] = field(default_factory=dict)
    
    # Daily stats
    daily_collections: int = 0
    daily_transfusions: int = 0
    daily_expired: int = 0
    daily_transfers_in: int = 0
    daily_transfers_out: int = 0
    
    # Modifiers
    flu_impact: float = 0.0  # 0-1, reduces donations
    weather_impact: float = 0.0  # 0-1, reduces donations
    
    def __post_init__(self):
        # Initialize inventory for each blood type if empty
        if not self.inventory:
            for bt, pct in BLOOD_TYPE_DISTRIBUTION.items():
                # Start with ~3 days of supply
                base_daily = (self.population / 100000) * BASE_DEMAND_PER_100K["RBC"] * pct
                initial_units = int(base_daily * 3)
                
                inv = BloodInventory(blood_type=bt, units_available=0)
                # Distribute initial inventory across ages
                for age in range(0, 21):  # Up to 3 weeks old
                    inv.add_units(int(initial_units / 21), age)
                
                inv.daily_demand = base_daily
                inv.calculate_days_of_supply()
                self.inventory[bt] = inv
    
    def simulate_day(self, 
                     flu_data: Optional[Dict] = None,
                     weather_data: Optional[Dict] = None,
                     shortage_data: Optional[Dict] = None,
                     event_modifier: float = 1.0) -> Dict:
        """
        Simulate one day of blood bank operations
        
        Args:
            flu_data: CDC flu data for the region
            weather_data: Weather impact data
            shortage_data: Known shortage information
            event_modifier: Multiplier for special events (mass casualty etc)
        
        Returns:
            Dict with simulation results
        """
        # Reset daily stats
        self.daily_collections = 0
        self.daily_transfusions = 0
        self.daily_expired = 0
        
        # Calculate modifiers
        self._update_modifiers(flu_data, weather_data)
        
        # Simulate for each blood type
        results = {}
        total_collections = 0
        total_demand = 0
        total_transfusions = 0
        total_expired = 0
        
        for bt, inv in self.inventory.items():
            # Age inventory first
            expired = inv.age_inventory()
            total_expired += expired
            
            # Calculate today's collections (with modifiers)
            collection_modifier = (1 - self.flu_impact * 0.3) * (1 - self.weather_impact * 0.5)
            collection_modifier *= self._get_seasonal_factor("donation")
            collection_modifier *= random.uniform(0.85, 1.15)  # Daily variance
            
            base_collections = inv.daily_demand * collection_modifier
            collections = int(max(0, base_collections + random.gauss(0, base_collections * 0.1)))
            inv.add_units(collections)
            total_collections += collections
            
            # Calculate today's demand (with event modifier)
            demand_modifier = self._get_seasonal_factor("demand")
            demand_modifier *= event_modifier
            demand_modifier *= random.uniform(0.9, 1.1)  # Daily variance
            
            # Weekend = less elective surgery = less demand
            if datetime.now().weekday() >= 5:
                demand_modifier *= 0.75
            
            demand = int(inv.daily_demand * demand_modifier)
            total_demand += demand
            
            # Fulfill demand
            transfused = inv.remove_units(demand)
            total_transfusions += transfused
            
            # Update days of supply
            inv.calculate_days_of_supply()
            
            results[bt] = {
                "units_available": inv.units_available,
                "days_of_supply": round(inv.days_of_supply, 2),
                "collected": collections,
                "transfused": transfused,
                "expired": expired,
                "unmet_demand": demand - transfused,
                "status": self._classify_status(inv.days_of_supply)
            }
        
        self.daily_collections = total_collections
        self.daily_transfusions = total_transfusions
        self.daily_expired = total_expired
        
        # Calculate overall status
        avg_days = sum(inv.days_of_supply for inv in self.inventory.values()) / len(self.inventory)
        min_days = min(inv.days_of_supply for inv in self.inventory.values())
        
        return {
            "region_id": self.region_id,
            "region_name": self.region_name,
            "date": datetime.now().isoformat(),
            "overall_days_of_supply": round(avg_days, 2),
            "critical_types": [bt for bt, inv in self.inventory.items() if inv.days_of_supply < 1.5],
            "status": self._classify_status(min_days),
            "total_collections": total_collections,
            "total_transfusions": total_transfusions,
            "total_expired": total_expired,
            "modifiers": {
                "flu_impact": round(self.flu_impact, 2),
                "weather_impact": round(self.weather_impact, 2)
            },
            "inventory": results
        }
    
    def _update_modifiers(self, flu_data: Optional[Dict], weather_data: Optional[Dict]):
        """Update flu and weather impact modifiers"""
        if flu_data:
            # Map flu activity to impact
            activity_map = {
                "minimal": 0.0,
                "low": 0.1,
                "moderate": 0.25,
                "high": 0.4,
                "very_high": 0.6
            }
            self.flu_impact = activity_map.get(flu_data.get("activity_level", "low"), 0.1)
        
        if weather_data:
            self.weather_impact = weather_data.get("impact_score", 0)
    
    def _get_seasonal_factor(self, factor_type: str) -> float:
        """Get seasonal adjustment factor"""
        month = datetime.now().month
        
        if month in [12, 1, 2]:
            season = "winter"
        elif month in [3, 4, 5]:
            season = "spring"
        elif month in [6, 7, 8]:
            season = "summer"
        else:
            season = "fall"
        
        return SEASONAL_FACTORS[season].get(factor_type, 1.0)
    
    def _classify_status(self, days_of_supply: float) -> str:
        """Classify supply status based on days of supply"""
        for status, (low, high) in SUPPLY_STATUS.items():
            if low <= days_of_supply < high:
                return status
        return "healthy"
    
    def transfer_to(self, other: 'RegionalBloodBank', blood_type: str, units: int) -> int:
        """Transfer units to another regional bank"""
        if blood_type not in self.inventory:
            return 0
        
        actual = self.inventory[blood_type].remove_units(units)
        other.inventory[blood_type].add_units(actual, age=1)  # Assume 1 day for transport
        
        self.daily_transfers_out += actual
        other.daily_transfers_in += actual
        
        return actual


class NationalBloodSimulation:
    """
    Manages simulation across all HHS regions
    """
    
    def __init__(self):
        self.regions: Dict[int, RegionalBloodBank] = {}
        self.history: List[Dict] = []
        self.current_day = 0
        
        # Initialize all regions
        for region_id, info in HHS_REGIONS.items():
            self.regions[region_id] = RegionalBloodBank(
                region_id=region_id,
                region_name=info["name"],
                population=info["population"]
            )
    
    def simulate_day(self, 
                     external_data: Optional[Dict] = None,
                     events: Optional[List[Dict]] = None) -> Dict:
        """
        Simulate one day across all regions
        
        Args:
            external_data: Dict with 'flu', 'weather', 'shortage' data by region
            events: List of special events (mass casualty, etc.)
        
        Returns:
            National simulation results
        """
        self.current_day += 1
        
        external_data = external_data or {}
        events = events or []
        
        # Process events to get regional modifiers
        event_modifiers = self._process_events(events)
        
        # Simulate each region
        regional_results = {}
        for region_id, bank in self.regions.items():
            flu_data = external_data.get("flu", {}).get(region_id, {})
            weather_data = external_data.get("weather", {}).get(region_id, {})
            shortage_data = external_data.get("shortage", {}).get(region_id, {})
            event_mod = event_modifiers.get(region_id, 1.0)
            
            result = bank.simulate_day(
                flu_data=flu_data,
                weather_data=weather_data,
                shortage_data=shortage_data,
                event_modifier=event_mod
            )
            regional_results[region_id] = result
        
        # Calculate national aggregates
        national = self._calculate_national_stats(regional_results)
        
        # Store in history
        day_record = {
            "day": self.current_day,
            "timestamp": datetime.now().isoformat(),
            "national": national,
            "regions": regional_results
        }
        self.history.append(day_record)
        
        return day_record
    
    def _process_events(self, events: List[Dict]) -> Dict[int, float]:
        """Process events and return demand modifiers by region"""
        modifiers = {r: 1.0 for r in range(1, 11)}
        
        for event in events:
            region = event.get("region_id")
            event_type = event.get("type", "")
            
            if region and region in modifiers:
                if event_type == "mass_casualty":
                    modifiers[region] *= event.get("severity", 2.0)
                elif event_type == "major_surgery_day":
                    modifiers[region] *= 1.3
                elif event_type == "holiday":
                    modifiers[region] *= 0.8  # Less elective surgery
        
        return modifiers
    
    def _calculate_national_stats(self, regional_results: Dict) -> Dict:
        """Calculate national aggregate statistics"""
        total_collections = sum(r["total_collections"] for r in regional_results.values())
        total_transfusions = sum(r["total_transfusions"] for r in regional_results.values())
        total_expired = sum(r["total_expired"] for r in regional_results.values())
        
        # Weighted average of days of supply
        total_pop = sum(HHS_REGIONS[r]["population"] for r in regional_results.keys())
        weighted_dos = sum(
            r["overall_days_of_supply"] * HHS_REGIONS[rid]["population"] 
            for rid, r in regional_results.items()
        ) / total_pop
        
        # Find critical regions
        critical_regions = [
            rid for rid, r in regional_results.items() 
            if r["status"] in ["critical", "low"]
        ]
        
        # Find critical blood types nationally
        critical_types = set()
        for r in regional_results.values():
            critical_types.update(r.get("critical_types", []))
        
        return {
            "overall_days_of_supply": round(weighted_dos, 2),
            "total_collections": total_collections,
            "total_transfusions": total_transfusions,
            "total_expired": total_expired,
            "critical_regions": critical_regions,
            "critical_blood_types": list(critical_types),
            "regions_in_shortage": len(critical_regions),
            "status": "critical" if len(critical_regions) > 3 else (
                "low" if len(critical_regions) > 0 else "adequate"
            )
        }
    
    def get_transfer_recommendations(self) -> List[Dict]:
        """
        Analyze current state and recommend inter-regional transfers
        """
        recommendations = []
        
        # Get current status for each region
        region_status = []
        for region_id, bank in self.regions.items():
            for bt, inv in bank.inventory.items():
                region_status.append({
                    "region_id": region_id,
                    "blood_type": bt,
                    "days_of_supply": inv.days_of_supply,
                    "units_available": inv.units_available
                })
        
        # Find regions with surplus that could help regions with shortage
        for bt in BLOOD_TYPE_DISTRIBUTION.keys():
            bt_data = [r for r in region_status if r["blood_type"] == bt]
            
            # Find shortage regions (< 1.5 days)
            shortage = [r for r in bt_data if r["days_of_supply"] < 1.5]
            # Find surplus regions (> 4 days)
            surplus = [r for r in bt_data if r["days_of_supply"] > 4]
            
            for short in shortage:
                for surp in surplus:
                    if surp["units_available"] > 100:  # Only if meaningful surplus
                        recommendations.append({
                            "from_region": surp["region_id"],
                            "to_region": short["region_id"],
                            "blood_type": bt,
                            "units_recommended": min(
                                int(surp["units_available"] * 0.1),  # Max 10% of surplus
                                100  # Cap at 100 units
                            ),
                            "priority": "high" if short["days_of_supply"] < 1 else "medium"
                        })
        
        # Sort by priority
        recommendations.sort(key=lambda x: (0 if x["priority"] == "high" else 1, -x["units_recommended"]))
        
        return recommendations[:10]  # Top 10 recommendations
    
    def get_current_state(self) -> Dict:
        """Get current state summary for all regions"""
        state = {}
        
        for region_id, bank in self.regions.items():
            region_inv = {}
            for bt, inv in bank.inventory.items():
                region_inv[bt] = {
                    "units": inv.units_available,
                    "days_of_supply": round(inv.days_of_supply, 2),
                    "status": "critical" if inv.days_of_supply < 1 else (
                        "low" if inv.days_of_supply < 2 else (
                            "adequate" if inv.days_of_supply < 3 else "healthy"
                        )
                    )
                }
            
            overall_dos = sum(i.days_of_supply for i in bank.inventory.values()) / len(bank.inventory)
            min_dos = min(i.days_of_supply for i in bank.inventory.values())
            
            state[region_id] = {
                "region_name": bank.region_name,
                "overall_days_of_supply": round(overall_dos, 2),
                "min_days_of_supply": round(min_dos, 2),
                "status": "critical" if min_dos < 1 else (
                    "low" if min_dos < 2 else "adequate"
                ),
                "inventory": region_inv,
                "modifiers": {
                    "flu_impact": bank.flu_impact,
                    "weather_impact": bank.weather_impact
                }
            }
        
        return state


def run_simulation_demo(days: int = 7) -> Dict:
    """
    Run a demo simulation for specified number of days
    """
    from data_sources import fetch_all_real_data
    
    # Initialize simulation
    sim = NationalBloodSimulation()
    
    # Fetch real data for modifiers
    print("Fetching external data...")
    external_data = fetch_all_real_data()
    
    # Run simulation
    print(f"Running {days}-day simulation...")
    results = []
    
    for day in range(days):
        print(f"  Day {day + 1}...")
        
        # Add random events occasionally
        events = []
        if random.random() < 0.1:  # 10% chance of event
            events.append({
                "type": "mass_casualty",
                "region_id": random.randint(1, 10),
                "severity": random.uniform(1.5, 3.0)
            })
        
        day_result = sim.simulate_day(
            external_data=external_data,
            events=events
        )
        results.append(day_result)
    
    # Get final state and recommendations
    final_state = sim.get_current_state()
    recommendations = sim.get_transfer_recommendations()
    
    return {
        "simulation_days": days,
        "daily_results": results,
        "final_state": final_state,
        "transfer_recommendations": recommendations
    }


if __name__ == "__main__":
    result = run_simulation_demo(days=3)
    print("\n=== Final State ===")
    print(json.dumps(result["final_state"], indent=2))
    print("\n=== Transfer Recommendations ===")
    print(json.dumps(result["transfer_recommendations"], indent=2))
