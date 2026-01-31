"""
Blood Bank Agent - Configuration and Constants
"""

# HHS Regions mapping
HHS_REGIONS = {
    1: {
        "name": "Region 1 - New England",
        "states": ["CT", "ME", "MA", "NH", "RI", "VT"],
        "major_centers": ["Rhode Island Blood Center", "American Red Cross NE"],
        "population": 14_850_000,
        "trauma_centers_l1_l2": 28
    },
    2: {
        "name": "Region 2 - NY/NJ",
        "states": ["NJ", "NY"],
        "major_centers": ["NY Blood Center", "NJ Blood Services"],
        "population": 28_500_000,
        "trauma_centers_l1_l2": 52
    },
    3: {
        "name": "Region 3 - Mid-Atlantic",
        "states": ["DE", "DC", "MD", "PA", "VA", "WV"],
        "major_centers": ["Blood Bank of Delmarva", "Inova Blood Services"],
        "population": 31_200_000,
        "trauma_centers_l1_l2": 48
    },
    4: {
        "name": "Region 4 - Southeast",
        "states": ["AL", "FL", "GA", "KY", "MS", "NC", "SC", "TN"],
        "major_centers": ["OneBlood", "The Blood Connection"],
        "population": 65_800_000,
        "trauma_centers_l1_l2": 95
    },
    5: {
        "name": "Region 5 - Midwest",
        "states": ["IL", "IN", "MI", "MN", "OH", "WI"],
        "major_centers": ["Versiti", "ImpactLife"],
        "population": 52_300_000,
        "trauma_centers_l1_l2": 78
    },
    6: {
        "name": "Region 6 - South Central",
        "states": ["AR", "LA", "NM", "OK", "TX"],
        "major_centers": ["Carter BloodCare", "LifeShare", "We Are Blood"],
        "population": 40_100_000,
        "trauma_centers_l1_l2": 62
    },
    7: {
        "name": "Region 7 - Central",
        "states": ["IA", "KS", "MO", "NE"],
        "major_centers": ["Community Blood Center KC", "Nebraska Community Blood Bank"],
        "population": 13_900_000,
        "trauma_centers_l1_l2": 22
    },
    8: {
        "name": "Region 8 - Mountain",
        "states": ["CO", "MT", "ND", "SD", "UT", "WY"],
        "major_centers": ["Vitalant"],
        "population": 12_400_000,
        "trauma_centers_l1_l2": 18
    },
    9: {
        "name": "Region 9 - Pacific Southwest",
        "states": ["AZ", "CA", "HI", "NV"],
        "major_centers": ["Vitalant", "Stanford Blood Center", "San Diego Blood Bank"],
        "population": 51_600_000,
        "trauma_centers_l1_l2": 85
    },
    10: {
        "name": "Region 10 - Pacific Northwest",
        "states": ["AK", "ID", "OR", "WA"],
        "major_centers": ["Bloodworks Northwest"],
        "population": 13_500_000,
        "trauma_centers_l1_l2": 20
    }
}

# Blood type distribution in US population
BLOOD_TYPE_DISTRIBUTION = {
    "O+": 0.374,
    "O-": 0.066,
    "A+": 0.316,
    "A-": 0.063,
    "B+": 0.094,
    "B-": 0.015,
    "AB+": 0.034,
    "AB-": 0.006
}

# Blood product shelf life (days)
SHELF_LIFE = {
    "RBC": 42,
    "Platelets": 5,
    "Plasma": 365,  # Frozen
    "Whole_Blood": 21
}

# Average daily demand per 100k population (units)
BASE_DEMAND_PER_100K = {
    "RBC": 8.5,
    "Platelets": 2.2,
    "Plasma": 1.8
}

# Seasonal adjustment factors (multiplier)
SEASONAL_FACTORS = {
    "winter": {"donation": 0.85, "demand": 1.05},  # Less donations, more accidents
    "spring": {"donation": 1.0, "demand": 1.0},
    "summer": {"donation": 0.88, "demand": 1.02},  # Vacations reduce donations
    "fall": {"donation": 1.0, "demand": 1.0}
}

# Blood center news URLs for scraping
BLOOD_CENTER_NEWS_URLS = {
    "Red Cross": "https://www.redcross.org/about-us/news-and-events/news.html",
    "NY Blood Center": "https://www.nybc.org/news/",
    "Vitalant": "https://www.vitalant.org/newsroom",
    "Versiti": "https://www.versiti.org/news",
    "OneBlood": "https://www.oneblood.org/about-us/newsroom/",
}

# CDC Delphi API endpoint
DELPHI_API_BASE = "https://api.delphi.cmu.edu/epidata"

# Status thresholds (days of supply)
SUPPLY_STATUS = {
    "critical": (0, 1),
    "low": (1, 2),
    "adequate": (2, 3),
    "healthy": (3, float('inf'))
}

# Agent action thresholds
AGENT_THRESHOLDS = {
    "issue_appeal": 1.5,  # Days of supply
    "transfer_trigger": 1.0,  # Days difference between regions
    "postpone_elective": 0.75  # Days of supply
}
