"""
Charity Intelligence Map — Geocoding Service
==============================================
Batch geocoding of UK postcodes using postcodes.io
(free, no API key required, CORS-enabled).
"""

import json
from urllib.request import Request, urlopen
from urllib.error import URLError
from typing import List, Dict, Optional

from backend.config import POSTCODES_IO_BULK, POSTCODES_IO_SINGLE, GEOCODE_BATCH_SIZE, GEOCODE_TIMEOUT
from backend.models import Charity, GeoLocation


def geocode_charities(charities: List[Charity]) -> List[Charity]:
    """
    Geocode all charities by their postcode using postcodes.io bulk API.

    Adds a GeoLocation to each charity that can be resolved.
    Returns only the charities that were successfully geocoded.
    """
    # Collect unique postcodes
    postcodes = list({c.postcode for c in charities if c.postcode})
    print(f"  Geocoding {len(postcodes)} unique postcodes...")

    # Bulk lookup
    pc_to_geo = _bulk_lookup(postcodes)

    # Attach results
    geocoded = 0
    results: List[Charity] = []

    for c in charities:
        geo = pc_to_geo.get(c.postcode)
        if geo:
            c.geo = geo
            geocoded += 1
            results.append(c)

    print(f"  ✓ Geocoded {geocoded}/{len(charities)} charities")
    return results


def geocode_single(postcode: str) -> Optional[GeoLocation]:
    """
    Geocode a single postcode. Used by the API for search requests.

    Returns GeoLocation or None if not found.
    """
    url = POSTCODES_IO_SINGLE.format(postcode=postcode.replace(" ", "%20"))
    try:
        with urlopen(url, timeout=GEOCODE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == 200 and data.get("result"):
            r = data["result"]
            return GeoLocation(
                lat=r["latitude"],
                lng=r["longitude"],
                district=r.get("admin_district", ""),
                ward=r.get("admin_ward", ""),
            )
    except Exception:
        pass
    return None


# ── Internal ────────────────────────────────────────────────────────────────

def _bulk_lookup(postcodes: List[str]) -> Dict[str, GeoLocation]:
    """
    Send postcodes in batches to the postcodes.io bulk endpoint.

    Returns dict mapping postcode string → GeoLocation.
    """
    results: Dict[str, GeoLocation] = {}

    for i in range(0, len(postcodes), GEOCODE_BATCH_SIZE):
        batch = postcodes[i: i + GEOCODE_BATCH_SIZE]
        batch_results = _send_batch(batch)
        results.update(batch_results)

        done = min(i + GEOCODE_BATCH_SIZE, len(postcodes))
        print(f"    {done}/{len(postcodes)} postcodes processed")

    return results


def _send_batch(postcodes: List[str]) -> Dict[str, GeoLocation]:
    """Send a single batch of postcodes to postcodes.io."""
    results: Dict[str, GeoLocation] = {}

    try:
        payload = json.dumps({"postcodes": postcodes}).encode("utf-8")
        req = Request(
            POSTCODES_IO_BULK,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(req, timeout=GEOCODE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") == 200:
            for item in data.get("result", []):
                if item.get("result"):
                    r = item["result"]
                    results[item["query"]] = GeoLocation(
                        lat=r["latitude"],
                        lng=r["longitude"],
                        district=r.get("admin_district", ""),
                        ward=r.get("admin_ward", ""),
                    )

    except (URLError, Exception) as e:
        print(f"    ✗ Batch geocoding failed: {e}")

    return results
