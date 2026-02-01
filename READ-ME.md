# 🎯 Charity Intelligence Map for Local Giving

**"Help donors fund the charities that need it most near them"**

A local impact discovery tool using **real public data** from the Charity Commission for England & Wales. Search by postcode, discover nearby charities ranked by need, and explore explainable financial intelligence.

---

## 📁 Project Structure

```
charity-intelligence-map/
│
├── backend/                    # Python backend modules
│   ├── __init__.py             # Package exports
│   ├── config.py               # All constants, URLs, thresholds, weights
│   ├── models.py               # Dataclasses: Charity, AnnualReturn, Anomaly, NeedScore
│   ├── data_sources.py         # Download, cache, parse CC bulk data
│   ├── processing.py           # Need score computation + anomaly detection
│   ├── geocoding.py            # Batch geocoding via postcodes.io
│   └── api.py                  # FastAPI REST server
│
├── frontend/                   # Browser-based dashboard
│   ├── index.html              # HTML shell (loads all modules)
│   ├── css/
│   │   └── styles.css          # All styles (extracted, standalone)
│   ├── js/
│   │   ├── app.js              # Main orchestrator — wires all modules
│   │   ├── map.js              # Leaflet map init, markers, search circle
│   │   ├── search.js           # Postcode geocoding via postcodes.io
│   │   ├── sidebar.js          # Charity list, borough summary, stats
│   │   ├── detail.js           # Full detail panel with score breakdown
│   │   ├── filters.js          # Category filter chips
│   │   └── utils.js            # Formatting, colours, haversine distance
│   └── data/
│       ├── demo_data.js        # Embedded demo dataset (20 real charities)
│       └── charities_data.js   # Generated: full processed dataset
│
├── prepare_data.py             # CLI: data pipeline entry point
├── run.py                      # CLI: start the API + frontend server
├── requirements.txt            # Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### Option 1: Static Demo (Zero Install)
```bash
cd frontend
# Serve with any static server:
python -m http.server 8080
# Open http://localhost:8080
```
The demo embeds ~20 real charities across London, Manchester, Bristol, Birmingham, Leeds, and Sheffield.

### Option 2: Full Data Pipeline
```bash
# No dependencies needed for the pipeline (stdlib only!)
python prepare_data.py

# Options:
python prepare_data.py --region london    # London charities only
python prepare_data.py --limit 2000       # Cap output size
python prepare_data.py --no-geocode       # Skip geocoding
python prepare_data.py --skip-download    # Re-process cached data
```

### Option 3: API Server
```bash
pip install -r requirements.txt
python run.py
# → http://localhost:8000       (dashboard)
# → http://localhost:8000/docs  (Swagger API docs)
```

---

## 🧩 Module Reference

### Backend

| Module | Responsibility |
|--------|---------------|
| **`config.py`** | All tunable parameters: API URLs, scoring weights, anomaly thresholds, classification codes. Change behavior here without touching logic. |
| **`models.py`** | Data structures: `Charity`, `AnnualReturn`, `Anomaly`, `NeedScore`, `GeoLocation`. Each has `.to_compact()` for frontend and `.to_full()` for API. |
| **`data_sources.py`** | Downloads CC bulk ZIPs, extracts TXT files, parses TSV, loads into model objects. Handles caching so re-runs skip downloads. |
| **`processing.py`** | Core intelligence: `compute_need_scores()` walks configurable thresholds; `_detect_anomalies()` applies rule-based pattern matching. |
| **`geocoding.py`** | Batch postcode → lat/lng via postcodes.io (free, no key). Handles 100-per-request batching. |
| **`api.py`** | FastAPI REST endpoints: `/api/search`, `/api/charity/{n}`, `/api/categories`, `/api/top`, `/api/stats`. Also serves the frontend. |

### Frontend

| Module | Responsibility |
|--------|---------------|
| **`app.js`** | Entry point. Loads data (API → file → demo fallback), wires events, orchestrates search → display flow. |
| **`map.js`** | Leaflet init, marker rendering with score-based colors/sizes, search radius circle, bounds fitting. |
| **`search.js`** | Postcode geocoding via `postcodes.io`. Handles full + partial codes. |
| **`sidebar.js`** | Renders ranked charity cards, borough summary, header stats. Uses event delegation for clicks. |
| **`detail.js`** | Full detail overlay: score breakdown bars, financial grid, history chart, anomaly alerts. |
| **`filters.js`** | Category chip generation, toggle state, filter application. |
| **`utils.js`** | `formatMoney()`, `getScoreColor()`, `haversine()`, `charityRegisterUrl()`. |

---

## 🧠 Intelligence Scoring

### Need Score (0–100)

Configurable in `backend/config.py` → `SCORE_WEIGHTS`:

| Factor | Max Pts | What It Measures |
|--------|---------|-----------------|
| `low_reserves` | 30 | Months of spending covered by reserves |
| `income_declining` | 25 | Year-over-year income trajectory |
| `overspending` | 20 | Spending-to-income ratio |
| `small_charity` | 15 | Income band (smaller = more marginal impact) |
| `late_filing` | 10 | Days since last annual return |

### Anomaly Detection

Configurable in `backend/config.py` → `ANOMALY_RULES`:

- 🔴 Critical reserves (<1 month)
- 🔴 Income drop (>30% YoY)
- 🟡 Spending mismatch (>130% of income)
- 🔵 Excessive reserves (>36 months — funds not reaching beneficiaries)
- 🔵 Income spike (>200% — may be one-off)

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check + loaded count |
| `GET` | `/api/search?postcode=SE1+7PB&radius=5` | Search charities near a postcode |
| `GET` | `/api/charity/1089464` | Single charity by registration number |
| `GET` | `/api/categories` | All categories with counts |
| `GET` | `/api/top?n=10&category=Relief+of+Poverty` | Top N by need score |
| `GET` | `/api/stats` | Aggregate dataset statistics |

---

## 📊 Data Sources

| Source | What | Auth |
|--------|------|------|
| [Charity Commission Bulk Data](https://register-of-charities.charitycommission.gov.uk/register/full-register-download) | 170K+ charity register with financials | None (OGL v3.0) |
| [postcodes.io](https://postcodes.io) | Postcode → coordinates | None (free) |
| [CartoDB Dark Matter](https://carto.com/basemaps) | Map tiles | None |

---

## 📜 Licence

- **Code**: MIT
- **Data**: Open Government Licence v3.0 (Crown Copyright, Charity Commission)
- **Map Tiles**: © OpenStreetMap contributors, © CARTO