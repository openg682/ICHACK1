"""
Blood Bank Agent - Autonomous Decision Making
The core agent that analyzes blood supply state and makes allocation decisions
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from config import HHS_REGIONS, AGENT_THRESHOLDS, BLOOD_TYPE_DISTRIBUTION
from simulation import NationalBloodSimulation


class ActionType(Enum):
    """Types of actions the agent can take"""
    ISSUE_SHORTAGE_APPEAL = "issue_shortage_appeal"
    TRANSFER_BLOOD = "transfer_blood"
    RECOMMEND_ELECTIVE_POSTPONEMENT = "recommend_elective_postponement"
    INCREASE_COLLECTION_EFFORT = "increase_collection_effort"
    NO_ACTION = "no_action"
    ALERT_CRITICAL = "alert_critical"


@dataclass
class AgentAction:
    """Represents an action decision by the agent"""
    action_type: ActionType
    region_id: Optional[int]
    blood_types: List[str]
    priority: str  # critical, high, medium, low
    reasoning: str
    details: Dict
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "action": self.action_type.value,
            "region_id": self.region_id,
            "blood_types": self.blood_types,
            "priority": self.priority,
            "reasoning": self.reasoning,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class BloodBankAgent:
    """
    Autonomous agent for blood bank management
    Analyzes supply state and makes decisions about:
    - Issuing shortage appeals
    - Recommending inter-regional transfers
    - Suggesting elective surgery postponements
    - Prioritizing collection efforts
    """
    
    def __init__(self, simulation: NationalBloodSimulation):
        self.simulation = simulation
        self.action_history: List[AgentAction] = []
        self.thresholds = AGENT_THRESHOLDS
    
    def analyze_and_act(self, external_context: Optional[Dict] = None) -> List[AgentAction]:
        """
        Main entry point: analyze current state and generate actions
        
        Args:
            external_context: Additional context (forecast, events, etc.)
        
        Returns:
            List of actions the agent recommends taking
        """
        actions = []
        
        # Get current state
        state = self.simulation.get_current_state()
        
        # Analyze each region
        for region_id, region_state in state.items():
            region_actions = self._analyze_region(region_id, region_state, external_context)
            actions.extend(region_actions)
        
        # Analyze national-level opportunities
        national_actions = self._analyze_national(state, external_context)
        actions.extend(national_actions)
        
        # Prioritize and deduplicate actions
        actions = self._prioritize_actions(actions)
        
        # Store in history
        self.action_history.extend(actions)
        
        return actions
    
    def _analyze_region(self, 
                       region_id: int, 
                       region_state: Dict,
                       context: Optional[Dict]) -> List[AgentAction]:
        """Analyze a single region and generate actions"""
        actions = []
        
        min_dos = region_state["min_days_of_supply"]
        overall_dos = region_state["overall_days_of_supply"]
        status = region_state["status"]
        
        # Find critical blood types
        critical_types = [
            bt for bt, inv in region_state["inventory"].items()
            if inv["days_of_supply"] < self.thresholds["issue_appeal"]
        ]
        
        # Check for critical shortage requiring immediate action
        if min_dos < 0.75:
            actions.append(AgentAction(
                action_type=ActionType.ALERT_CRITICAL,
                region_id=region_id,
                blood_types=critical_types,
                priority="critical",
                reasoning=f"Region {region_id} has critically low supply ({min_dos:.1f} days). "
                         f"Immediate action required for {', '.join(critical_types)}. "
                         f"Patient care may be impacted without intervention.",
                details={
                    "min_days_of_supply": min_dos,
                    "affected_types": critical_types,
                    "recommended_immediate_actions": [
                        "Contact neighboring regions for emergency transfer",
                        "Issue urgent public appeal",
                        "Notify hospitals to delay non-critical transfusions"
                    ]
                }
            ))
            
            # Also recommend elective postponement
            actions.append(AgentAction(
                action_type=ActionType.RECOMMEND_ELECTIVE_POSTPONEMENT,
                region_id=region_id,
                blood_types=critical_types,
                priority="critical",
                reasoning=f"With only {min_dos:.1f} days of supply for {', '.join(critical_types)}, "
                         f"elective surgeries using these blood types should be postponed.",
                details={
                    "estimated_savings_per_day": len(critical_types) * 15,  # ~15 units per type
                    "duration_recommended": "Until supply reaches 2+ days"
                }
            ))
        
        # Check if shortage appeal is needed
        elif min_dos < self.thresholds["issue_appeal"]:
            # Determine appeal urgency
            if min_dos < 1.0:
                urgency = "urgent"
                priority = "high"
            else:
                urgency = "needed"
                priority = "medium"
            
            actions.append(AgentAction(
                action_type=ActionType.ISSUE_SHORTAGE_APPEAL,
                region_id=region_id,
                blood_types=critical_types,
                priority=priority,
                reasoning=f"Region {region_id} ({HHS_REGIONS[region_id]['name']}) has {min_dos:.1f} days "
                         f"of supply for {', '.join(critical_types)}. Public donation appeal is {urgency}.",
                details={
                    "current_supply_days": min_dos,
                    "target_supply_days": 3.0,
                    "units_needed": self._estimate_units_needed(region_id, critical_types, 3.0),
                    "suggested_messaging": self._generate_appeal_message(region_id, critical_types, min_dos)
                }
            ))
        
        # Check modifiers for proactive collection
        flu_impact = region_state.get("modifiers", {}).get("flu_impact", 0)
        weather_impact = region_state.get("modifiers", {}).get("weather_impact", 0)
        
        if flu_impact > 0.3 or weather_impact > 0.3:
            if overall_dos < 3.0:
                actions.append(AgentAction(
                    action_type=ActionType.INCREASE_COLLECTION_EFFORT,
                    region_id=region_id,
                    blood_types=list(BLOOD_TYPE_DISTRIBUTION.keys()),
                    priority="medium",
                    reasoning=f"Region {region_id} is experiencing collection headwinds "
                             f"(flu impact: {flu_impact:.0%}, weather: {weather_impact:.0%}) "
                             f"with only {overall_dos:.1f} days of supply. "
                             f"Proactive collection measures recommended.",
                    details={
                        "flu_impact": flu_impact,
                        "weather_impact": weather_impact,
                        "suggested_actions": [
                            "Increase targeted outreach to regular donors",
                            "Consider mobile drive rescheduling",
                            "Partner with corporate sponsors for drive hosting"
                        ]
                    }
                ))
        
        return actions
    
    def _analyze_national(self, 
                         state: Dict, 
                         context: Optional[Dict]) -> List[AgentAction]:
        """Analyze national-level transfer opportunities"""
        actions = []
        
        # Get transfer recommendations from simulation
        transfers = self.simulation.get_transfer_recommendations()
        
        for transfer in transfers[:5]:  # Top 5 transfers
            from_region = transfer["from_region"]
            to_region = transfer["to_region"]
            blood_type = transfer["blood_type"]
            units = transfer["units_recommended"]
            priority = transfer["priority"]
            
            # Verify the transfer makes sense
            from_state = state[from_region]
            to_state = state[to_region]
            
            from_dos = from_state["inventory"][blood_type]["days_of_supply"]
            to_dos = to_state["inventory"][blood_type]["days_of_supply"]
            
            # Only recommend if differential is significant
            if from_dos - to_dos > 1.5:
                actions.append(AgentAction(
                    action_type=ActionType.TRANSFER_BLOOD,
                    region_id=None,  # National action
                    blood_types=[blood_type],
                    priority=priority,
                    reasoning=f"Transfer {units} units of {blood_type} from Region {from_region} "
                             f"({HHS_REGIONS[from_region]['name']}, {from_dos:.1f} days) to "
                             f"Region {to_region} ({HHS_REGIONS[to_region]['name']}, {to_dos:.1f} days). "
                             f"This balances supply across regions.",
                    details={
                        "from_region": from_region,
                        "from_region_name": HHS_REGIONS[from_region]["name"],
                        "to_region": to_region,
                        "to_region_name": HHS_REGIONS[to_region]["name"],
                        "units": units,
                        "from_days_supply": from_dos,
                        "to_days_supply": to_dos,
                        "estimated_cost": units * 50  # ~$50 per unit shipping
                    }
                ))
        
        return actions
    
    def _prioritize_actions(self, actions: List[AgentAction]) -> List[AgentAction]:
        """Sort and deduplicate actions by priority"""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        
        # Sort by priority
        actions.sort(key=lambda a: priority_order.get(a.priority, 4))
        
        # Deduplicate similar actions (same type, region, blood types)
        seen = set()
        unique_actions = []
        
        for action in actions:
            key = (action.action_type, action.region_id, tuple(sorted(action.blood_types)))
            if key not in seen:
                seen.add(key)
                unique_actions.append(action)
        
        return unique_actions
    
    def _estimate_units_needed(self, 
                              region_id: int, 
                              blood_types: List[str],
                              target_days: float) -> Dict[str, int]:
        """Estimate units needed to reach target days of supply"""
        bank = self.simulation.regions[region_id]
        needed = {}
        
        for bt in blood_types:
            if bt in bank.inventory:
                inv = bank.inventory[bt]
                current_days = inv.days_of_supply
                if current_days < target_days:
                    units_gap = int(inv.daily_demand * (target_days - current_days))
                    needed[bt] = max(0, units_gap)
        
        return needed
    
    def _generate_appeal_message(self, 
                                region_id: int, 
                                blood_types: List[str],
                                days_supply: float) -> str:
        """Generate a public appeal message"""
        region_name = HHS_REGIONS[region_id]["name"]
        
        if days_supply < 1:
            urgency = "URGENT"
            timeframe = "immediately"
        elif days_supply < 1.5:
            urgency = "Critical"
            timeframe = "this week"
        else:
            urgency = "Needed"
            timeframe = "soon"
        
        types_str = ", ".join(blood_types)
        
        message = (
            f"{urgency}: Blood donors needed in {region_name}! "
            f"We have less than {days_supply:.1f} days of {types_str} blood supply. "
            f"If you're able, please donate {timeframe}. "
            f"Your donation can save up to 3 lives. "
            f"Visit your local blood center or call 1-800-RED-CROSS to schedule."
        )
        
        return message
    
    def get_summary(self) -> Dict:
        """Get a summary of agent state and recent actions"""
        recent_actions = self.action_history[-20:]  # Last 20 actions
        
        action_counts = {}
        for action in recent_actions:
            action_type = action.action_type.value
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        critical_count = sum(1 for a in recent_actions if a.priority == "critical")
        high_count = sum(1 for a in recent_actions if a.priority == "high")
        
        return {
            "total_actions_taken": len(self.action_history),
            "recent_actions": len(recent_actions),
            "action_breakdown": action_counts,
            "critical_actions": critical_count,
            "high_priority_actions": high_count,
            "last_action_time": self.action_history[-1].timestamp.isoformat() if self.action_history else None
        }
    
    def explain_decision(self, action: AgentAction) -> str:
        """Generate a human-readable explanation of a decision"""
        explanation = f"""
## Agent Decision: {action.action_type.value.replace('_', ' ').title()}

**Priority:** {action.priority.upper()}
**Region:** {HHS_REGIONS[action.region_id]['name'] if action.region_id else 'National'}
**Blood Types Affected:** {', '.join(action.blood_types)}

### Reasoning
{action.reasoning}

### Recommended Actions
"""
        if action.details.get("suggested_actions"):
            for i, act in enumerate(action.details["suggested_actions"], 1):
                explanation += f"{i}. {act}\n"
        
        if action.details.get("units_needed"):
            explanation += "\n### Units Needed\n"
            for bt, units in action.details["units_needed"].items():
                explanation += f"- {bt}: {units} units\n"
        
        return explanation


def run_agent_demo():
    """
    Run a demonstration of the agent making decisions
    """
    from data_sources import fetch_all_real_data
    
    print("=" * 60)
    print("BLOOD BANK AGENT - AUTONOMOUS DECISION MAKING DEMO")
    print("=" * 60)
    
    # Initialize simulation
    print("\nInitializing national blood supply simulation...")
    sim = NationalBloodSimulation()
    
    # Fetch external data
    print("Fetching real-world data (CDC flu, weather)...")
    external_data = fetch_all_real_data()
    
    # Run a few days of simulation to create interesting state
    print("Running 5-day simulation to establish state...")
    for day in range(5):
        # Occasionally inject a crisis event
        events = []
        if day == 3:
            events.append({
                "type": "mass_casualty",
                "region_id": 4,  # Southeast
                "severity": 2.5
            })
        
        sim.simulate_day(external_data=external_data, events=events)
    
    # Initialize agent
    print("\nInitializing autonomous agent...")
    agent = BloodBankAgent(sim)
    
    # Get agent decisions
    print("\nAgent analyzing current state and generating actions...")
    actions = agent.analyze_and_act(external_context=external_data)
    
    # Display results
    print("\n" + "=" * 60)
    print(f"AGENT GENERATED {len(actions)} ACTIONS")
    print("=" * 60)
    
    for i, action in enumerate(actions, 1):
        print(f"\n--- Action {i} ---")
        print(f"Type: {action.action_type.value}")
        print(f"Priority: {action.priority.upper()}")
        if action.region_id:
            print(f"Region: {HHS_REGIONS[action.region_id]['name']}")
        print(f"Blood Types: {', '.join(action.blood_types)}")
        print(f"\nReasoning: {action.reasoning}")
        
        if action.details.get("suggested_messaging"):
            print(f"\nSuggested Public Message:")
            print(f"  \"{action.details['suggested_messaging']}\"")
    
    # Print agent summary
    print("\n" + "=" * 60)
    print("AGENT SUMMARY")
    print("=" * 60)
    summary = agent.get_summary()
    print(json.dumps(summary, indent=2))
    
    return agent, sim


if __name__ == "__main__":
    agent, sim = run_agent_demo()
