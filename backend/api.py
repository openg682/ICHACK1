"""
Charity Intelligence Map — REST API
=====================================
FastAPI server exposing charity data, search, and scoring endpoints.

Endpoints:
    GET  /api/health                Health check
    GET  /api/meta                  Dataset metadata
    GET  /api/search?postcode=...   Search charities near a postcode
    GET  /api/charity/{number}      Get a single charity by registration number
    GET  /api/categories            List all category counts
    GET  /api/top?n=10              Top N charities by need score

Run:
    uvicorn backend.api:app --reload
"""

import os
import json
import math
from typing import Optional

try:
    from fastapi import FastAPI, Query, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from backend.config import API_HOST, API_PORT, API_CORS_ORIGINS, OUTPUT_JSON, PROJECT_ROOT


# ═══════════════════════════════════════════════════════════════════════════
# DATA STORE (loaded once at startup)
# ═══════════════════════════════════════════════════════════════════════════

_charities: list[dict] = []
_by_number: dict[str, dict] = {}
_meta: dict = {}


def _load_data():
    """Load processed charity data from the JSON output file."""
    global _charities, _by_number, _meta

    if not os.path.exists(OUTPUT_JSON):
        print(f"⚠ No data file found at {OUTPUT_JSON}")
        print("  Run `python prepare_data.py` first to generate the dataset.")
        return

    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    _meta = data.get("meta", {})
    _charities = data.get("charities", [])
    _by_number = {c["n"]: c for c in _charities}

    print(f"✓ Loaded {len(_charities)} charities from {OUTPUT_JSON}")


# ═══════════════════════════════════════════════════════════════════════════
# HAVERSINE DISTANCE
# ═══════════════════════════════════════════════════════════════════════════

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km between two lat/lng points."""
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (
        math.sin(dLat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dLon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ═══════════════════════════════════════════════════════════════════════════
# APP FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def create_app() -> "FastAPI":
    """Create and configure the FastAPI application."""
    if not HAS_FASTAPI:
        raise ImportError(
            "FastAPI is required for the API server. "
            "Install with: pip install fastapi uvicorn"
        )

    app = FastAPI(
        title="Charity Intelligence Map API",
        description="Find and score charities by need near any UK postcode",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=API_CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load data on startup
    @app.on_event("startup")
    async def startup():
        _load_data()

    # ── Serve frontend ──
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    app.mount(
        "/static",
        StaticFiles(directory=frontend_dir),
        name="static",
    )

    # ── API Routes ──

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "charities_loaded": len(_charities)}

    @app.get("/api/meta")
    async def meta():
        return {
            **_meta,
            "charities_loaded": len(_charities),
        }

    @app.get("/api/search")
    async def search(
        postcode: str = Query(None, description="UK postcode to search near"),
        lat: Optional[float] = Query(None, description="Latitude"),
        lng: Optional[float] = Query(None, description="Longitude"),
        radius: float = Query(5.0, ge=0.5, le=50, description="Search radius in km"),
        category: Optional[str] = Query(None, description="Filter by category"),
        min_score: int = Query(0, ge=0, le=100, description="Minimum need score"),
        limit: int = Query(50, ge=1, le=200, description="Max results"),
        sort: str = Query("need_score", description="Sort by: need_score, distance, income"),
    ):
        """Search for charities near a postcode or coordinate."""
        # Resolve postcode to coordinates
        if postcode and (lat is None or lng is None):
            from backend.geocoding import geocode_single

            geo = geocode_single(postcode)
            if not geo:
                raise HTTPException(status_code=404, detail="Postcode not found")
            lat, lng = geo.lat, geo.lng
            area_name = geo.district
        elif lat is not None and lng is not None:
            area_name = "Custom location"
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either a postcode or lat/lng coordinates",
            )

        # Find nearby charities
        results = []
        for c in _charities:
            c_lat = c.get("lat")
            c_lng = c.get("lng")
            if c_lat is None or c_lng is None:
                continue

            dist = _haversine(lat, lng, c_lat, c_lng)
            if dist > radius:
                continue

            if category and category not in (c.get("cat") or []):
                continue

            score = c.get("ns", 0)
            if score < min_score:
                continue

            results.append({**c, "distance": round(dist, 2)})

        # Sort
        if sort == "distance":
            results.sort(key=lambda x: x["distance"])
        elif sort == "income":
            results.sort(key=lambda x: x.get("inc", 0), reverse=True)
        else:
            results.sort(key=lambda x: x.get("ns", 0), reverse=True)

        return {
            "center": {"lat": lat, "lng": lng},
            "area": area_name if postcode else None,
            "radius_km": radius,
            "total": len(results),
            "charities": results[:limit],
        }

    @app.get("/api/charity/{charity_number}")
    async def get_charity(charity_number: str):
        """Get detailed info for a single charity by registration number."""
        c = _by_number.get(charity_number)
        if not c:
            raise HTTPException(status_code=404, detail="Charity not found")
        return c

    @app.get("/api/categories")
    async def categories():
        """List all categories with counts."""
        counts: dict[str, int] = {}
        for c in _charities:
            for cat in c.get("cat", []):
                counts[cat] = counts.get(cat, 0) + 1
        sorted_cats = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return {"categories": [{"name": k, "count": v} for k, v in sorted_cats]}

    @app.get("/api/top")
    async def top_charities(
        n: int = Query(10, ge=1, le=100),
        category: Optional[str] = None,
    ):
        """Get the top N charities by need score."""
        filtered = _charities
        if category:
            filtered = [c for c in filtered if category in (c.get("cat") or [])]

        sorted_list = sorted(filtered, key=lambda x: x.get("ns", 0), reverse=True)
        return {"total": len(sorted_list), "charities": sorted_list[:n]}

    @app.get("/api/stats")
    async def stats():
        """Aggregate statistics across the loaded dataset."""
        if not _charities:
            return {"error": "No data loaded"}

        scores = [c.get("ns", 0) for c in _charities]
        incomes = [c.get("inc", 0) for c in _charities if c.get("inc", 0) > 0]
        with_anomalies = sum(1 for c in _charities if c.get("an"))

        return {
            "total_charities": len(_charities),
            "avg_need_score": round(sum(scores) / len(scores), 1),
            "median_need_score": sorted(scores)[len(scores) // 2],
            "high_need_count": sum(1 for s in scores if s >= 50),
            "with_anomalies": with_anomalies,
            "total_income": sum(incomes),
            "median_income": sorted(incomes)[len(incomes) // 2] if incomes else 0,
        }

    return app


# ── Module-level app instance for `uvicorn backend.api:app` ──
if HAS_FASTAPI:
    app = create_app()