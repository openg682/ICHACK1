"""
Charity Intelligence Map — Data Models
=======================================
Dataclass definitions for all structured data flowing through the system.
Used by the processing pipeline and serialised to JSON for the frontend.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AnnualReturn:
    """A single year's financial return from the Charity Commission."""
    fin_period_end: str          # ISO date string
    income: float = 0.0
    spending: float = 0.0
    ar_cycle: str = ""

    def to_compact(self) -> dict:
        """Compact dict for frontend (minimise JSON size)."""
        return {
            "d": self.fin_period_end[:10],
            "i": round(self.income),
            "e": round(self.spending),
        }


@dataclass
class Anomaly:
    """A detected anomaly flag on a charity's financials."""
    type: str                    # e.g. "income_drop", "critical_reserves"
    severity: str                # "high", "medium", "low"
    detail: str                  # Human-readable explanation

    def to_dict(self) -> dict:
        return {"type": self.type, "severity": self.severity, "detail": self.detail}


@dataclass
class NeedScore:
    """Composite need score with its constituent factors."""
    total: int = 0
    factors: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"total": self.total, "factors": self.factors}


@dataclass
class GeoLocation:
    """Geocoded postcode result."""
    lat: float
    lng: float
    district: str = ""
    ward: str = ""


@dataclass
class Charity:
    """
    Full charity record combining register data, financials,
    classifications, computed scores, and anomalies.
    """
    # ── Identity ──
    charity_number: str
    name: str
    postcode: str = ""
    company_number: str = ""
    date_registered: str = ""
    date_removed: str = ""
    reporting_status: str = ""
    activities: str = ""

    # ── Financials ──
    income: float = 0.0
    spending: float = 0.0
    reserves: float = 0.0
    employees: int = 0
    volunteers: int = 0

    # ── Classifications ──
    categories: list[str] = field(default_factory=list)      # What
    beneficiaries: list[str] = field(default_factory=list)    # Who
    methods: list[str] = field(default_factory=list)          # How

    # ── History ──
    annual_returns: list[AnnualReturn] = field(default_factory=list)
    area_of_operation: list[str] = field(default_factory=list)

    # ── Computed ──
    need_score: Optional[NeedScore] = None
    anomalies: list[Anomaly] = field(default_factory=list)
    reserves_months: Optional[float] = None
    income_trend: Optional[float] = None
    spending_ratio: Optional[float] = None

    # ── Geo ──
    geo: Optional[GeoLocation] = None

    def to_compact(self) -> dict:
        """
        Serialise to a compact dictionary for the frontend.
        Keys are abbreviated to minimise JSON payload.
        """
        d = {
            "n":   self.charity_number,
            "nm":  self.name,
            "pc":  self.postcode,
            "inc": round(self.income),
            "exp": round(self.spending),
            "res": round(self.reserves),
            "emp": self.employees,
            "vol": self.volunteers,
            "cat": self.categories[:3],
            "ben": self.beneficiaries[:2],
            "act": self.activities[:200],
            "reg": self.date_registered[:10] if self.date_registered else "",
            "ns":  self.need_score.total if self.need_score else 0,
            "nf":  self.need_score.factors if self.need_score else {},
            "rm":  self.reserves_months,
            "it":  self.income_trend,
            "sr":  self.spending_ratio,
            "an":  [a.to_dict() for a in self.anomalies],
            "ar":  [ar.to_compact() for ar in self.annual_returns[:5]],
        }

        if self.geo and self.geo.lat is not None and self.geo.lng is not None:
            d["lat"] = round(self.geo.lat, 5)
            d["lng"] = round(self.geo.lng, 5)
            d["dist"] = self.geo.district or ""
            d["ward"] = self.geo.ward or ""

        return d

    def to_full(self) -> dict:
        """Full dictionary for API responses (not abbreviated)."""
        return {
            "charity_number": self.charity_number,
            "name": self.name,
            "postcode": self.postcode,
            "company_number": self.company_number,
            "date_registered": self.date_registered,
            "activities": self.activities,
            "income": self.income,
            "spending": self.spending,
            "reserves": self.reserves,
            "employees": self.employees,
            "volunteers": self.volunteers,
            "categories": self.categories,
            "beneficiaries": self.beneficiaries,
            "methods": self.methods,
            "annual_returns": [ar.to_compact() for ar in self.annual_returns],
            "area_of_operation": self.area_of_operation,
            "need_score": self.need_score.total if self.need_score else 0,
            "need_factors": self.need_score.factors if self.need_score else {},
            "reserves_months": self.reserves_months,
            "income_trend": self.income_trend,
            "spending_ratio": self.spending_ratio,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "latitude": self.geo.lat if self.geo else None,
            "longitude": self.geo.lng if self.geo else None,
            "district": self.geo.district if self.geo else None,
        }