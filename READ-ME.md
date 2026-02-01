# 🎯 Charity Intelligence Map for Local Giving

**"Help donors fund the charities that need it most near them"**

A local impact discovery tool that uses **real public data** from the Charity Commission for England & Wales to find nearby charities, categorise them, and flag which ones appear underfunded or highly active based on objective financial signals.

![Licence](https://img.shields.io/badge/data-Open%20Government%20Licence%20v3.0-blue)
![Charities](https://img.shields.io/badge/charities-170%2C000%2B-green)

---

## 🚀 Quick Start

### Option 1: Demo (Instant)
Just open `index.html` in any modern browser. The demo includes ~50 real charities across London, Manchester, Bristol, Birmingham, Leeds, and Sheffield.

1. Open `index.html`
2. Enter a UK postcode (try **SE1 7PB**, **E1 6AN**, **M1 1AD**, **BS1 1JG**)
3. Explore charities ranked by need score

### Option 2: Full Dataset (Recommended)
Run the data pipeline to download and process the **full Charity Commission register** (170,000+ charities):

```bash
# Install dependencies (just Python standard library!)
python prepare_data.py

# Or filter to London only:
python prepare_data.py --region london

# Or limit output:
python prepare_data.py --limit 2000
```

This downloads ~200MB of data from the Charity Commission, processes it into a compact JSON, and the dashboard automatically picks it up.

---

## 🧠 Intelligence Features

### Need Score (0–100)
A composite score identifying charities that may benefit most from additional donations:

| Factor | Max Points | Signal |
|--------|-----------|--------|
| **Reserves Level** | 30 | Low reserves (<3 months of spending) = high need |
| **Income Trend** | 25 | Declining income year-over-year = growing need |
| **Spending vs Income** | 20 | Spending exceeding income = stretching resources |
| **Organisation Size** | 15 | Smaller charities = more marginal impact per £ |
| **Filing Recency** | 10 | Late/missing filings = potential struggle |

### Anomaly Detection
Automatically flags charities with unusual financial patterns:
- 🔴 **Critical reserves** — Less than 1 month of operating costs saved
- 🔴 **Income drop** — >30% year-over-year decline
- 🟡 **Spending mismatch** — Expenditure significantly exceeding income
- 🟡 **Late filing** — Annual returns overdue
- 🔵 **Excessive reserves** — >36 months of spending saved (funds not reaching beneficiaries)
- 🔵 **Income spike** — >200% increase (may be one-off grant, not sustainable)

### Category Clustering
Charities are classified by:
- **What** they do (14 categories: health, education, poverty relief, etc.)
- **Who** they help (7 beneficiary types)
- **How** they operate (10 methods)

---

## 📐 Architecture

```
charity-intelligence-map/
├── index.html              ← Main dashboard (standalone, works offline)
├── prepare_data.py         ← Data pipeline for real CC data
├── charities_data.js       ← Generated: processed data for dashboard
├── charities_data.json     ← Generated: same data in JSON format
└── README.md
```

### Data Flow
```
Charity Commission Bulk Download (daily extract)
    ↓
prepare_data.py
    ├── Downloads: charity, annual_return_history, classification, areas
    ├── Parses: tab-delimited text files
    ├── Joins: charity info + financials + categories
    ├── Computes: need scores, anomaly detection
    ├── Geocodes: postcodes.io (free, no key needed)
    └── Outputs: charities_data.js / .json
    ↓
index.html (dashboard)
    ├── Loads: embedded data or charities_data.js
    ├── Search: postcodes.io for postcode → lat/lng
    ├── Map: Leaflet + CartoDB Dark Matter tiles
    ├── Ranking: charities by need score
    └── Detail: financial analysis + anomaly flags
```

### External APIs Used
| API | Purpose | Auth Required? |
|-----|---------|---------------|
| [postcodes.io](https://postcodes.io) | Postcode → coordinates | No (free, CORS-enabled) |
| [Charity Commission Data](https://register-of-charities.charitycommission.gov.uk/register/full-register-download) | Charity register bulk data | No (Open Government Licence) |
| [CartoDB Tiles](https://carto.com/basemaps) | Map tiles | No |

---

## 🔬 Methodology

### Need Score Algorithm

The need score is designed to identify **marginal impact** — where your £1 donation makes the biggest difference:

**Reserves Ratio** (up to 30 points):
- `reserves_months = (reserves / annual_spending) × 12`
- <1 month → 30pts, <3 months → 20pts, <6 months → 10pts

**Income Trend** (up to 25 points):
- Year-over-year income change from annual returns
- <-30% → 25pts, <-10% → 15pts, <0% → 5pts

**Spending Efficiency** (up to 20 points):
- `spend_ratio = spending / income`
- >1.2 → 20pts (burning through reserves), >1.0 → 10pts

**Size Factor** (up to 15 points):
- Income <£10k → 15pts, <£100k → 10pts, <£1m → 5pts
- Smaller charities have less fundraising capacity

**Filing Recency** (up to 10 points):
- Days since last annual return
- >2 years → 10pts, >18 months → 5pts

### Anomaly Detection

Simple rule-based anomaly detection (not "fraud accusations", just "worth reviewing"):
- Statistical outliers in reserves-to-spending ratio
- Sudden changes in income trajectory
- Mismatches between income and expenditure
- Very high reserves relative to charitable spending

---

## 📊 Data Source

All charity data comes from the **Charity Commission for England & Wales**, which maintains the register of approximately 170,000 charities. The data is published under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

The register includes:
- Charity name, registration number, and contact details
- Financial data from annual returns (income, expenditure, reserves)
- Classification (purpose, beneficiaries, operating methods)
- Trustee information
- Filing history

---

## 🛠️ Hackathon Notes

**Why this matters for effective giving:**
- Classic charity optimisation problem: maximise marginal impact of donations
- Transparency + accountability: all data is public and verifiable
- Explainable scoring: every charity's need score breaks down into clear factors
- Local focus: helps donors find charities in their community, not just big nationals

**Demo flow:**
1. Pick a borough (e.g., Tower Hamlets, Hackney, Islington)
2. Show top 10 charities by need score
3. Click any charity to see **why** it scored high (explainable features)
4. Compare financial trajectories across years
5. Identify anomalies worth investigating
6. Link directly to Charity Commission register for verification

---

## 📜 Licence

- **Code**: MIT
- **Data**: Open Government Licence v3.0 (Crown Copyright, Charity Commission)
- **Map Tiles**: © OpenStreetMap contributors, © CARTO