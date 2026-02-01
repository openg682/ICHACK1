#!/usr/bin/env python3
"""
Charity Intelligence Map — Data Preparation Pipeline
=====================================================
Downloads, processes, and exports real Charity Commission data.

Usage:
    python prepare_data.py                    # Full pipeline
    python prepare_data.py --skip-download    # Re-process cached data
    python prepare_data.py --region london    # Filter to London only
    python prepare_data.py --limit 500        # Cap output charities
    python prepare_data.py --no-geocode       # Skip geocoding step
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.config import OUTPUT_JS, OUTPUT_JSON, OUTPUT_DIR
from backend.data_sources import (
    download_all,
    load_charities,
    load_classifications,
    load_annual_returns,
    load_parta_returns,
    load_areas_of_operation,
)
from backend.processing import compute_need_scores, filter_viable_charities
from backend.geocoding import geocode_charities


def write_output(charities, output_js, output_json):
    """Write processed data as JS + JSON files for the frontend."""
    os.makedirs(os.path.dirname(output_js), exist_ok=True)

    # Use your method to convert Charity objects to compact dicts
    compact = [c.to_compact() for c in charities]
    now = datetime.now()

    # JavaScript version (embeddable)
    js_content = (
        f"// Charity Intelligence Map — Processed Data\n"
        f"// Source: Charity Commission for England & Wales (OGL v3.0)\n"
        f"// Generated: {now.strftime('%Y-%m-%d %H:%M')}\n"
        f"// Charities: {len(compact)}\n\n"
        f"var CHARITY_DATA = {json.dumps(compact, separators=(',', ':'))};\n"
        f"var DATA_META = {json.dumps({'source': 'Charity Commission for England & Wales', 'licence': 'Open Government Licence v3.0', 'generated': now.isoformat(), 'count': len(compact), 'isRealData': True}, separators=(',', ':'))};\n"
    )

    with open(output_js, "w", encoding="utf-8") as f:
        f.write(js_content)

    # JSON version (for API)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "meta": {
                    "source": "Charity Commission for England & Wales",
                    "licence": "Open Government Licence v3.0",
                    "generated": now.isoformat(),
                    "count": len(compact),
                },
                "charities": compact,
            },
            f,
            separators=(",", ":"),
        )

    js_mb = os.path.getsize(output_js) / 1e6
    json_mb = os.path.getsize(output_json) / 1e6
    print(f"\n  ✓ JS output:   {output_js} ({js_mb:.1f} MB)")
    print(f"  ✓ JSON output: {output_json} ({json_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(
        description="Charity Intelligence Map — Data Pipeline"
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="Skip downloading, use cached data files",
    )
    parser.add_argument(
        "--region", type=str, default=None, choices=["london"],
        help="Filter charities to a specific region",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit the number of output charities",
    )
    parser.add_argument(
        "--no-geocode", action="store_true",
        help="Skip the geocoding step",
    )
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════╗")
    print("║  Charity Intelligence Map — Data Pipeline        ║")
    print("║  Real data from Charity Commission (E&W)         ║")
    print("╚══════════════════════════════════════════════════╝")

    # ── Step 1: Download ──
    if not args.skip_download:
        print("\n── Step 1: Downloading datasets ──")
        download_all()
    else:
        print("\n── Step 1: Skipped (using cached data) ──")

    # ── Step 2: Load raw data ──
    print("\n── Step 2: Loading charity register ──")
    charities = load_charities(region=args.region)

    if not charities:
        print("\n✗ No charities loaded. Check that data files exist in data_cache/")
        sys.exit(1)

    print("\n── Step 3: Loading supplementary data ──")
    load_classifications(charities)
    load_annual_returns(charities)
    load_parta_returns(charities)
    load_areas_of_operation(charities)

    # ── Step 4: Process ──
    print("\n── Step 4: Computing need scores & anomalies ──")
    compute_need_scores(charities)
    viable = filter_viable_charities(charities)
    print(f"  Viable charities with financials: {len(viable)}")

    if args.limit:
        viable = viable[: args.limit]
        print(f"  Limited to top {args.limit}")

    # ── Step 5: Geocode ──
    if not args.no_geocode:
        print("\n── Step 5: Geocoding postcodes ──")
        viable = geocode_charities(viable)
    else:
        print("\n── Step 5: Skipped geocoding ──")

    # ── Step 6: Output ──
    print("\n── Step 6: Writing output ──")
    write_output(viable, OUTPUT_JS, OUTPUT_JSON)

    # ── Summary ──
    scores = [c.need_score.total for c in viable if c.need_score]
    high_need = sum(1 for s in scores if s >= 50)
    with_anomalies = sum(1 for c in viable if c.anomalies)

    print(f"\n── Summary ──")
    print(f"  Total charities:    {len(viable)}")
    print(f"  High need (≥50):    {high_need}")
    print(f"  With anomalies:     {with_anomalies}")
    if scores:
        print(f"  Avg need score:     {sum(scores)/len(scores):.1f}")
    print(f"\n✓ Done! Run the app with: python run.py")


if __name__ == "__main__":
    main()
