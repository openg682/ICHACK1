#!/usr/bin/env python3
"""
Charity Intelligence Map - Data Preparation Pipeline
=====================================================
Downloads and processes REAL data from the Charity Commission for England & Wales.
Computes need scores, anomaly detection, and outputs a compact JSON for the dashboard.

Data source: Charity Commission Register (Open Government Licence v3.0)
https://register-of-charities.charitycommission.gov.uk/register/full-register-download

Usage:
    python prepare_data.py                    # Full pipeline
    python prepare_data.py --skip-download    # Re-process existing downloads
    python prepare_data.py --region london    # Filter to London only
    python prepare_data.py --limit 500        # Limit output charities
"""

import os
import io
import sys
import json
import zipfile
import argparse
import math
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.request import urlretrieve
from urllib.error import URLError

# ─── Configuration ───────────────────────────────────────────────────────────

BASE_URL = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/txt"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charities_data.js")

DATASETS = {
    "charity": f"{BASE_URL}/publicextract.charity.zip",
    "charity_annual_return_history": f"{BASE_URL}/publicextract.charity_annual_return_history.zip",
    "charity_annual_return_parta": f"{BASE_URL}/publicextract.charity_annual_return_parta.zip",
    "charity_classification": f"{BASE_URL}/publicextract.charity_classification.zip",
    "charity_area_of_operation": f"{BASE_URL}/publicextract.charity_area_of_operation.zip",
}

# Classification codes from Charity Commission
CLASSIFICATION_TYPES = {
    "What": {
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
    },
    "Who": {
        "201": "Children/Young People",
        "202": "Elderly/Old People",
        "203": "People with Disabilities",
        "204": "People of a Particular Ethnic or Racial Origin",
        "205": "Other Charities/Voluntary Bodies",
        "206": "Other Defined Groups",
        "207": "The General Public/Mankind",
    },
    "How": {
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
    },
}

# London postcodes (outward codes)
LONDON_OUTWARD = set()
for prefix in ["E", "EC", "N", "NW", "SE", "SW", "W", "WC"]:
    for i in range(30):
        LONDON_OUTWARD.add(f"{prefix}{i}")
    LONDON_OUTWARD.add(prefix)


# ─── Download ────────────────────────────────────────────────────────────────

def download_datasets():
    """Download all required datasets from the Charity Commission."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    for name, url in DATASETS.items():
        zip_path = os.path.join(DATA_DIR, f"{name}.zip")
        txt_path = os.path.join(DATA_DIR, f"{name}.txt")
        
        if os.path.exists(txt_path):
            print(f"  ✓ {name} already extracted")
            continue
        
        if not os.path.exists(zip_path):
            print(f"  ↓ Downloading {name}...")
            try:
                urlretrieve(url, zip_path)
                print(f"    Downloaded {os.path.getsize(zip_path) / 1e6:.1f} MB")
            except URLError as e:
                print(f"    ✗ Failed to download {name}: {e}")
                continue
        
        # Extract
        print(f"  ⤳ Extracting {name}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                members = z.namelist()
                for member in members:
                    if member.endswith('.txt') or member.endswith('.csv'):
                        with z.open(member) as src:
                            content = src.read()
                        with open(txt_path, 'wb') as dst:
                            dst.write(content)
                        break
                else:
                    # Extract first file regardless
                    with z.open(members[0]) as src:
                        content = src.read()
                    with open(txt_path, 'wb') as dst:
                        dst.write(content)
            print(f"    Extracted to {txt_path}")
        except Exception as e:
            print(f"    ✗ Failed to extract {name}: {e}")


# ─── Parse ───────────────────────────────────────────────────────────────────

def parse_tsv(filepath, max_rows=None):
    """Parse a tab-delimited file into list of dicts."""
    rows = []
    try:
        with open(filepath, 'r', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for i, row in enumerate(reader):
                if max_rows and i >= max_rows:
                    break
                rows.append(row)
    except FileNotFoundError:
        print(f"  ✗ File not found: {filepath}")
    return rows


def safe_float(val, default=0.0):
    """Safely convert to float."""
    if val is None:
        return default
    try:
        cleaned = str(val).strip().replace(',', '').replace('£', '')
        if cleaned in ('', '-', 'N/A', 'None'):
            return default
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    """Safely convert to int."""
    return int(safe_float(val, default))


# ─── Process ─────────────────────────────────────────────────────────────────

def process_charities(region=None, limit=None):
    """Process all datasets and compute intelligence metrics."""
    
    print("\n── Loading charity register ──")
    charity_file = os.path.join(DATA_DIR, "charity.txt")
    charities_raw = parse_tsv(charity_file)
    print(f"  Loaded {len(charities_raw)} charity records")
    
    # Filter to registered charities only
    charities = {}
    for c in charities_raw:
        status = (c.get('charity_registration_status') or '').strip()
        if status.lower() != 'registered':
            continue
        
        charity_num = (c.get('registered_charity_number') or '').strip()
        if not charity_num:
            continue
        
        postcode = (c.get('charity_contact_postcode') or '').strip().upper()
        
        # Region filter
        if region == 'london':
            outward = postcode.split()[0] if ' ' in postcode else postcode[:len(postcode)-3].strip()
            if outward not in LONDON_OUTWARD:
                continue
        
        name = (c.get('charity_name') or '').strip()
        if not name:
            continue
        
        charities[charity_num] = {
            'charity_number': charity_num,
            'name': name,
            'postcode': postcode,
            'income': safe_float(c.get('latest_income')),
            'spending': safe_float(c.get('latest_expenditure')),
            'date_registered': (c.get('date_of_registration') or '').strip(),
            'date_removed': (c.get('date_of_removal') or '').strip(),
            'activities': (c.get('charity_activities') or '').strip()[:300],
            'company_number': (c.get('charity_company_registration_number') or '').strip(),
            'reporting_status': (c.get('charity_reporting_status') or '').strip(),
            'categories': [],
            'beneficiaries': [],
            'methods': [],
            'annual_returns': [],
            'area_of_operation': [],
        }
    
    print(f"  Active charities: {len(charities)}")
    
    # ── Load classifications ──
    print("\n── Loading classifications ──")
    class_file = os.path.join(DATA_DIR, "charity_classification.txt")
    classifications = parse_tsv(class_file)
    print(f"  Loaded {len(classifications)} classification records")
    
    for cl in classifications:
        cnum = (cl.get('registered_charity_number') or '').strip()
        if cnum not in charities:
            continue
        
        cls_type = (cl.get('classification_type') or '').strip()
        cls_code = (cl.get('classification_code') or '').strip()
        cls_desc = (cl.get('classification_description') or '').strip()
        
        if cls_type == 'What':
            charities[cnum]['categories'].append(cls_desc or CLASSIFICATION_TYPES.get('What', {}).get(cls_code, 'Unknown'))
        elif cls_type == 'Who':
            charities[cnum]['beneficiaries'].append(cls_desc or CLASSIFICATION_TYPES.get('Who', {}).get(cls_code, 'Unknown'))
        elif cls_type == 'How':
            charities[cnum]['methods'].append(cls_desc or CLASSIFICATION_TYPES.get('How', {}).get(cls_code, 'Unknown'))
    
    # ── Load financial history ──
    print("\n── Loading annual return history ──")
    ar_file = os.path.join(DATA_DIR, "charity_annual_return_history.txt")
    annual_returns = parse_tsv(ar_file)
    print(f"  Loaded {len(annual_returns)} annual return records")
    
    for ar in annual_returns:
        cnum = (ar.get('registered_charity_number') or '').strip()
        if cnum not in charities:
            continue
        
        charities[cnum]['annual_returns'].append({
            'fin_period_end': (ar.get('fin_period_end_date') or '').strip(),
            'income': safe_float(ar.get('total_gross_income')),
            'spending': safe_float(ar.get('total_gross_expenditure')),
            'ar_cycle': (ar.get('ar_cycle_reference') or '').strip(),
        })
    
    # ── Load Part A returns (reserves, employees, volunteers) ──
    print("\n── Loading Part A returns ──")
    parta_file = os.path.join(DATA_DIR, "charity_annual_return_parta.txt")
    parta_returns = parse_tsv(parta_file)
    print(f"  Loaded {len(parta_returns)} Part A records")
    
    # Index by charity number - keep latest
    parta_by_charity = {}
    for pa in parta_returns:
        cnum = (pa.get('registered_charity_number') or '').strip()
        if cnum not in charities:
            continue
        
        fin_end = (pa.get('fin_period_end_date') or '').strip()
        if cnum not in parta_by_charity or fin_end > parta_by_charity[cnum].get('fin_period_end', ''):
            parta_by_charity[cnum] = {
                'fin_period_end': fin_end,
                'total_income': safe_float(pa.get('total_gross_income')),
                'total_spending': safe_float(pa.get('total_gross_expenditure')),
                'reserves': safe_float(pa.get('reserves')),
                'employees': safe_int(pa.get('count_employees')),
                'volunteers': safe_int(pa.get('count_volunteers')),
            }
    
    # Merge Part A data
    for cnum, pa_data in parta_by_charity.items():
        if cnum in charities:
            charities[cnum]['reserves'] = pa_data['reserves']
            charities[cnum]['employees'] = pa_data['employees']
            charities[cnum]['volunteers'] = pa_data['volunteers']
            if pa_data['total_income'] > 0:
                charities[cnum]['income'] = pa_data['total_income']
            if pa_data['total_spending'] > 0:
                charities[cnum]['spending'] = pa_data['total_spending']
    
    # ── Load areas of operation ──
    print("\n── Loading areas of operation ──")
    area_file = os.path.join(DATA_DIR, "charity_area_of_operation.txt")
    areas = parse_tsv(area_file)
    print(f"  Loaded {len(areas)} area records")
    
    for a in areas:
        cnum = (a.get('registered_charity_number') or '').strip()
        if cnum not in charities:
            continue
        area_name = (a.get('geographic_area_description') or '').strip()
        if area_name:
            charities[cnum]['area_of_operation'].append(area_name)
    
    # ── Compute Intelligence Metrics ──
    print("\n── Computing need scores & anomaly detection ──")
    
    results = []
    for cnum, c in charities.items():
        # Skip charities with zero financials
        if c['income'] <= 0 and c['spending'] <= 0:
            continue
        
        # Skip if no postcode
        if not c['postcode']:
            continue
        
        # Sort annual returns by date
        c['annual_returns'].sort(key=lambda x: x['fin_period_end'], reverse=True)
        
        # ── Compute Need Score (0-100, higher = more need) ──
        need_factors = {}
        
        # 1. Reserves ratio (reserves / annual spending)
        reserves = c.get('reserves', 0)
        spending = c.get('spending', 0)
        if spending > 0 and reserves >= 0:
            reserves_months = (reserves / spending) * 12
            if reserves_months < 1:
                need_factors['low_reserves'] = 30
            elif reserves_months < 3:
                need_factors['low_reserves'] = 20
            elif reserves_months < 6:
                need_factors['low_reserves'] = 10
            else:
                need_factors['low_reserves'] = 0
            c['reserves_months'] = round(reserves_months, 1)
        else:
            c['reserves_months'] = None
        
        # 2. Income trend (year-over-year)
        if len(c['annual_returns']) >= 2:
            latest = c['annual_returns'][0]['income']
            previous = c['annual_returns'][1]['income']
            if previous > 0:
                income_change = (latest - previous) / previous
                c['income_trend'] = round(income_change, 3)
                if income_change < -0.3:
                    need_factors['income_declining'] = 25
                elif income_change < -0.1:
                    need_factors['income_declining'] = 15
                elif income_change < 0:
                    need_factors['income_declining'] = 5
                else:
                    need_factors['income_declining'] = 0
            else:
                c['income_trend'] = None
        else:
            c['income_trend'] = None
        
        # 3. Spending efficiency (spending / income)
        income = c.get('income', 0)
        if income > 0:
            spend_ratio = spending / income
            c['spending_ratio'] = round(spend_ratio, 3)
            if spend_ratio > 1.2:
                need_factors['overspending'] = 20
            elif spend_ratio > 1.0:
                need_factors['overspending'] = 10
            else:
                need_factors['overspending'] = 0
        else:
            c['spending_ratio'] = None
        
        # 4. Size factor (smaller charities need more marginal help)
        if income < 10000:
            need_factors['small_charity'] = 15
        elif income < 100000:
            need_factors['small_charity'] = 10
        elif income < 1000000:
            need_factors['small_charity'] = 5
        else:
            need_factors['small_charity'] = 0
        
        # 5. Filing recency
        if c['annual_returns']:
            latest_date_str = c['annual_returns'][0]['fin_period_end']
            try:
                latest_date = datetime.strptime(latest_date_str[:10], '%Y-%m-%d')
                days_since = (datetime.now() - latest_date).days
                if days_since > 730:  # Over 2 years
                    need_factors['late_filing'] = 10
                elif days_since > 547:  # Over 18 months
                    need_factors['late_filing'] = 5
                else:
                    need_factors['late_filing'] = 0
            except (ValueError, TypeError):
                need_factors['late_filing'] = 0
        
        # Compute total need score
        need_score = min(100, sum(need_factors.values()))
        c['need_score'] = need_score
        c['need_factors'] = need_factors
        
        # ── Anomaly Detection ──
        anomalies = []
        
        # Sudden income drop
        if c.get('income_trend') is not None and c['income_trend'] < -0.3:
            anomalies.append({
                'type': 'income_drop',
                'severity': 'high' if c['income_trend'] < -0.5 else 'medium',
                'detail': f"Income dropped {abs(c['income_trend'])*100:.0f}% year-over-year"
            })
        
        # Very low reserves
        if c.get('reserves_months') is not None and c['reserves_months'] < 1:
            anomalies.append({
                'type': 'critical_reserves',
                'severity': 'high',
                'detail': f"Only {c['reserves_months']:.1f} months of reserves"
            })
        
        # Very high reserves (potential dormancy)
        if c.get('reserves_months') is not None and c['reserves_months'] > 36:
            anomalies.append({
                'type': 'excessive_reserves',
                'severity': 'low',
                'detail': f"{c['reserves_months']:.0f} months of reserves — funds may not be reaching beneficiaries"
            })
        
        # Spending exceeds income significantly
        if c.get('spending_ratio') is not None and c['spending_ratio'] > 1.3:
            anomalies.append({
                'type': 'spending_mismatch',
                'severity': 'medium',
                'detail': f"Spending {c['spending_ratio']*100:.0f}% of income"
            })
        
        # Income spike (could be one-off grant)
        if c.get('income_trend') is not None and c['income_trend'] > 2.0:
            anomalies.append({
                'type': 'income_spike',
                'severity': 'low',
                'detail': f"Income increased {c['income_trend']*100:.0f}% — may be a one-off"
            })
        
        c['anomalies'] = anomalies
        
        # ── Build output record ──
        record = {
            'n': c['charity_number'],     # charity number
            'nm': c['name'],              # name
            'pc': c['postcode'],          # postcode
            'inc': round(c['income']),
            'exp': round(c['spending']),
            'res': round(c.get('reserves', 0)),
            'emp': c.get('employees', 0),
            'vol': c.get('volunteers', 0),
            'cat': c['categories'][:3],   # top 3 categories
            'ben': c['beneficiaries'][:2],
            'act': c['activities'][:200],
            'reg': c['date_registered'][:10] if c['date_registered'] else '',
            'ns': c['need_score'],
            'nf': c['need_factors'],
            'rm': c['reserves_months'],
            'it': c['income_trend'],
            'sr': c['spending_ratio'],
            'an': c['anomalies'],
            'ar': [{'d': ar['fin_period_end'][:10], 'i': round(ar['income']), 'e': round(ar['spending'])} 
                   for ar in c['annual_returns'][:5]],  # Last 5 years
        }
        results.append(record)
    
    # Sort by need score (descending)
    results.sort(key=lambda x: x['ns'], reverse=True)
    
    if limit:
        results = results[:limit]
    
    print(f"  Processed {len(results)} charities with financials")
    
    return results


# ─── Geocoding ───────────────────────────────────────────────────────────────

def batch_geocode(charities, batch_size=100):
    """
    Geocode postcodes using postcodes.io (free, no API key needed).
    Adds lat/lng to each charity record.
    """
    from urllib.request import Request, urlopen
    
    print(f"\n── Geocoding {len(charities)} postcodes ──")
    
    postcodes = list(set(c['pc'] for c in charities if c['pc']))
    pc_to_coords = {}
    
    for i in range(0, len(postcodes), batch_size):
        batch = postcodes[i:i+batch_size]
        try:
            payload = json.dumps({"postcodes": batch}).encode('utf-8')
            req = Request(
                "https://api.postcodes.io/postcodes",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            
            if data.get('status') == 200:
                for result in data.get('result', []):
                    if result.get('result'):
                        r = result['result']
                        pc_to_coords[result['query']] = {
                            'lat': r['latitude'],
                            'lng': r['longitude'],
                            'district': r.get('admin_district', ''),
                            'ward': r.get('admin_ward', ''),
                        }
            
            done = min(i + batch_size, len(postcodes))
            print(f"  Geocoded {done}/{len(postcodes)} postcodes")
            
        except Exception as e:
            print(f"  ✗ Geocoding batch failed: {e}")
    
    # Merge coords into charity records
    geocoded = 0
    for c in charities:
        coords = pc_to_coords.get(c['pc'])
        if coords:
            c['lat'] = round(coords['lat'], 5)
            c['lng'] = round(coords['lng'], 5)
            c['dist'] = coords['district']
            c['ward'] = coords['ward']
            geocoded += 1
        else:
            c['lat'] = None
            c['lng'] = None
    
    # Remove un-geocodable charities
    charities = [c for c in charities if c.get('lat') is not None]
    print(f"  Successfully geocoded {geocoded} charities")
    
    return charities


# ─── Output ──────────────────────────────────────────────────────────────────

def write_output(charities):
    """Write processed data as a JavaScript file for the dashboard."""
    
    # Write as JS variable for easy embedding
    js_content = f"""// Charity Intelligence Map - Processed Data
// Source: Charity Commission for England & Wales (Open Government Licence v3.0)
// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
// Charities: {len(charities)}

const CHARITY_DATA = {json.dumps(charities, separators=(',', ':'))};
const DATA_META = {{
    source: "Charity Commission for England & Wales",
    licence: "Open Government Licence v3.0",
    generated: "{datetime.now().isoformat()}",
    count: {len(charities)},
    isRealData: true
}};
"""
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    size_mb = os.path.getsize(OUTPUT_FILE) / 1e6
    print(f"\n✓ Output written to {OUTPUT_FILE} ({size_mb:.1f} MB)")
    print(f"  {len(charities)} charities with full intelligence metrics")
    
    # Also write a plain JSON version
    json_path = OUTPUT_FILE.replace('.js', '.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'meta': {
                'source': 'Charity Commission for England & Wales',
                'licence': 'Open Government Licence v3.0',
                'generated': datetime.now().isoformat(),
                'count': len(charities),
            },
            'charities': charities,
        }, f, separators=(',', ':'))
    print(f"  JSON version: {json_path}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Charity Intelligence Map - Data Pipeline')
    parser.add_argument('--skip-download', action='store_true', help='Skip downloading, use cached data')
    parser.add_argument('--region', type=str, default=None, choices=['london'], help='Filter to region')
    parser.add_argument('--limit', type=int, default=None, help='Limit output charities')
    parser.add_argument('--no-geocode', action='store_true', help='Skip geocoding step')
    args = parser.parse_args()
    
    print("╔══════════════════════════════════════════════╗")
    print("║  Charity Intelligence Map - Data Pipeline    ║")
    print("║  Real data from Charity Commission (E&W)     ║")
    print("╚══════════════════════════════════════════════╝")
    
    # Step 1: Download
    if not args.skip_download:
        print("\n── Step 1: Downloading datasets ──")
        download_datasets()
    else:
        print("\n── Step 1: Skipping download (using cached data) ──")
    
    # Step 2: Process
    print("\n── Step 2: Processing charities ──")
    charities = process_charities(region=args.region, limit=args.limit)
    
    if not charities:
        print("\n✗ No charities processed. Check that data files exist in data_cache/")
        sys.exit(1)
    
    # Step 3: Geocode
    if not args.no_geocode:
        charities = batch_geocode(charities)
    
    # Step 4: Output
    print("\n── Step 4: Writing output ──")
    write_output(charities)
    
    # Summary stats
    scores = [c['ns'] for c in charities]
    high_need = sum(1 for s in scores if s >= 50)
    with_anomalies = sum(1 for c in charities if c.get('an'))
    
    print(f"\n── Summary ──")
    print(f"  Total charities: {len(charities)}")
    print(f"  High need (score ≥50): {high_need}")
    print(f"  With anomalies: {with_anomalies}")
    print(f"  Avg need score: {sum(scores)/len(scores):.1f}")
    print(f"\n✓ Done! Open index.html to view the dashboard.")


if __name__ == '__main__':
    main()