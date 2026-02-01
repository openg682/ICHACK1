"""
Charity Intelligence Map — Configuration
=========================================
All constants, API endpoints, classification codes, scoring thresholds,
and tunable parameters live here. Change these to adjust behavior
without touching any other module.
"""

import os

# ─── Paths ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data_cache")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "frontend", "data")
OUTPUT_JS = os.path.join(OUTPUT_DIR, "charities_data.js")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "charities_data.json")


# ─── Charity Commission Data Sources ────────────────────────────────────────

CC_BLOB_BASE = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/txt"

DATASETS = {
    "charity": {
        "url": f"{CC_BLOB_BASE}/publicextract.charity.zip",
        "description": "Main charity register — names, status, financials, contacts",
    },
    "charity_annual_return_history": {
        "url": f"{CC_BLOB_BASE}/publicextract.charity_annual_return_history.zip",
        "description": "Year-by-year income/expenditure for each charity",
    },
    "charity_annual_return_parta": {
        "url": f"{CC_BLOB_BASE}/publicextract.charity_annual_return_parta.zip",
        "description": "Part A returns — reserves, employee counts, volunteer counts",
    },
    "charity_classification": {
        "url": f"{CC_BLOB_BASE}/publicextract.charity_classification.zip",
        "description": "What / Who / How classification codes",
    },
    "charity_area_of_operation": {
        "url": f"{CC_BLOB_BASE}/publicextract.charity_area_of_operation.zip",
        "description": "Geographic areas where charities operate",
    },
}


# ─── Geocoding ──────────────────────────────────────────────────────────────

POSTCODES_IO_BULK = "https://api.postcodes.io/postcodes"
POSTCODES_IO_SINGLE = "https://api.postcodes.io/postcodes/{postcode}"
GEOCODE_BATCH_SIZE = 100   # postcodes.io accepts up to 100 per request
GEOCODE_TIMEOUT = 30       # seconds


# ─── API Server ─────────────────────────────────────────────────────────────

API_HOST = "0.0.0.0"
API_PORT = 8000
API_CORS_ORIGINS = ["*"]


# ─── Classification Codes ───────────────────────────────────────────────────
# From Charity Commission data definitions

CLASSIFICATION_WHAT = {
    "101": "General Charitable Purposes",
    "102": "Education/Training",
    "103": "Medical/Health/Sickness",
    "104": "Disability",
    "105": "Relief of Poverty",
    "106": "Overseas Aid/Famine Relief",
    "107": "Accommodation/Housing",
    "108": "Religious Activities",
    "109": "Arts/Culture/Heritage/Science",
    "110": "Amateur Sport",
    "111": "Animals",
    "112": "Environment/Conservation/Heritage",
    "113": "Economic/Community Development/Employment",
    "114": "Armed Forces/Emergency Service Efficiency",
    "115": "Human Rights/Religious/Racial Harmony/Equality/Diversity",
    "116": "Recreation",
    "117": "Other Charitable Purposes",
}

CLASSIFICATION_WHO = {
    "201": "Children/Young People",
    "202": "Elderly/Old People",
    "203": "People with Disabilities",
    "204": "People of a Particular Ethnic or Racial Origin",
    "205": "Other Charities/Voluntary Bodies",
    "206": "Other Defined Groups",
    "207": "The General Public/Mankind",
}

CLASSIFICATION_HOW = {
    "301": "Makes Grants to Individuals",
    "302": "Makes Grants to Organisations",
    "303": "Provides Other Finance",
    "304": "Provides Human Resources",
    "305": "Provides Buildings/Facilities/Open Space",
    "306": "Provides Services",
    "307": "Provides Advocacy/Advice/Information",
    "308": "Sponsors or Undertakes Research",
    "309": "Acts as an Umbrella or Resource Body",
    "310": "Other Charitable Activities",
}


# ─── Viability Filters ──────────────────────────────────────────────────────
# Charities below these thresholds are excluded from results entirely.
DEFAULT_MIN_SPENDING = 5_000  # £3k minimum annual spending to be included


SCORE_WEIGHTS = {
    "low_reserves": {
        "max": 15,
        "range": (1.0, 6.0),        # <1 month = max points, >6 months = 0
        "direction": "lower_is_worse",
    },
    "income_declining": {
        "max": 15,
        "range": (-0.30, -0.05),    # drop >30% = max points
        "direction": "lower_is_worse",
    },
    "overspending": {
        "max": 15,
        "range": (1.20, 1.50),      # 120–150% spending triggers
        "direction": "higher_is_worse",
    },
    "small_charity": {
        "max": 5,
        "range": (5_000, 50_000),   # under 5k = max points, >50k = 0
        "direction": "lower_is_worse",
    },
    "late_filing": {
        "max": 5,
        "range": (730, 1095),       # 2–3 years overdue
        "direction": "higher_is_worse",
    },
    "multi_year_decline": {
        "max": 5,
        "range": (2, 3),            # 2–3 years declining
        "direction": "higher_is_worse",
    },
}

# Percentile normalization: still enabled, but distribution bands slightly adjusted
SCORE_NORMALIZATION = {
    "enabled": True,
    "bands": {
        "critical": 85,   # top 15% → scores 85-100
        "high":     65,   # next 20% → 65-84
        "medium":   35,   # next 35% → 35-64
        "low":      0,    # bottom 30% → 0-34
    },
}



# ─── Anomaly Detection Thresholds ───────────────────────────────────────────

ANOMALY_RULES = {
    "income_drop": {
        "description": "Sudden income decline",
        "field": "income_trend",
        "conditions": [
            {"threshold": -0.50, "severity": "high",   "template": "Income dropped {pct:.0f}% year-over-year"},
            {"threshold": -0.30, "severity": "medium",  "template": "Income dropped {pct:.0f}% year-over-year"},
        ],
    },
    "critical_reserves": {
        "description": "Dangerously low reserves",
        "field": "reserves_months",
        "conditions": [
            {"threshold": 1.0, "severity": "high", "template": "Only {val:.1f} months of reserves"},
        ],
    },
    "excessive_reserves": {
        "description": "Funds potentially not reaching beneficiaries",
        "field": "reserves_months",
        "conditions": [
            {"threshold": 36.0, "severity": "low", "operator": "gt",
             "template": "{val:.0f} months of reserves — funds may not be reaching beneficiaries"},
        ],
    },
    "spending_mismatch": {
        "description": "Expenditure significantly exceeds income",
        "field": "spending_ratio",
        "conditions": [
            {"threshold": 1.30, "severity": "medium", "operator": "gt",
             "template": "Spending {pct:.0f}% of income"},
        ],
    },
    "income_spike": {
        "description": "Unusual income increase (may be one-off)",
        "field": "income_trend",
        "conditions": [
            {"threshold": 2.0, "severity": "low", "operator": "gt",
             "template": "Income increased {pct:.0f}% — may be a one-off"},
        ],
    },
}


# ─── London Outward Postcode Codes ──────────────────────────────────────────

LONDON_OUTWARD_PREFIXES = ["E", "EC", "N", "NW", "SE", "SW", "W", "WC"]

def build_london_outward_set():
    """Build set of valid London outward codes for filtering."""
    codes = set()
    for prefix in LONDON_OUTWARD_PREFIXES:
        for i in range(30):
            codes.add(f"{prefix}{i}")
        codes.add(prefix)
    return codes

LONDON_OUTWARD = build_london_outward_set()