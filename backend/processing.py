"""
Charity Intelligence Map — Processing Engine
==============================================
Computes need scores and detects anomalies for each charity
based on their financial data and filing history.

All scoring thresholds are defined in config.py and can be
adjusted without modifying this module.
"""

from datetime import datetime
from typing import Dict, List

from backend.config import SCORE_WEIGHTS, ANOMALY_RULES
from backend.models import Charity, NeedScore, Anomaly


# ═══════════════════════════════════════════════════════════════════════════
# NEED SCORE COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════

def compute_need_scores(charities: Dict[str, Charity]) -> None:
    """
    Compute the composite need score for every charity (mutates in-place).

    The need score (0–100) estimates how much marginal benefit an
    additional donation would provide, based on objective financial signals.
    """
    for c in charities.values():
        _compute_derived_metrics(c)
        _compute_score(c)
        _detect_anomalies(c)


def _compute_derived_metrics(c: Charity) -> None:
    """Compute intermediate financial metrics used by scoring and anomalies."""

    # Sort annual returns newest-first
    c.annual_returns.sort(key=lambda ar: ar.fin_period_end, reverse=True)

    # ── Reserves months ──
    if c.spending > 0 and c.reserves >= 0:
        c.reserves_months = round((c.reserves / c.spending) * 12, 1)
    else:
        c.reserves_months = None

    # ── Income trend (year-over-year) ──
    if len(c.annual_returns) >= 2:
        latest = c.annual_returns[0].income
        previous = c.annual_returns[1].income
        if previous > 0:
            c.income_trend = round((latest - previous) / previous, 3)
        else:
            c.income_trend = None
    else:
        c.income_trend = None

    # ── Spending ratio ──
    if c.income > 0:
        c.spending_ratio = round(c.spending / c.income, 3)
    else:
        c.spending_ratio = None


def _compute_score(c: Charity) -> None:
    """
    Apply the scoring rubric from SCORE_WEIGHTS to produce a 0–100 score.

    Each factor contributes points based on configurable thresholds.
    The total is capped at 100.
    """
    factors: Dict[str, int] = {}

    # ── Low reserves ──
    w = SCORE_WEIGHTS["low_reserves"]
    if c.reserves_months is not None:
        factors["low_reserves"] = _threshold_score(
            c.reserves_months, w["thresholds"], w["default"], comparison="lt"
        )
    else:
        factors["low_reserves"] = 0

    # ── Income declining ──
    w = SCORE_WEIGHTS["income_declining"]
    if c.income_trend is not None:
        factors["income_declining"] = _threshold_score(
            c.income_trend, w["thresholds"], w["default"], comparison="lt"
        )
    else:
        factors["income_declining"] = 0

    # ── Overspending ──
    w = SCORE_WEIGHTS["overspending"]
    if c.spending_ratio is not None:
        factors["overspending"] = _threshold_score(
            c.spending_ratio, w["thresholds"], w["default"], comparison="gt"
        )
    else:
        factors["overspending"] = 0

    # ── Small charity ──
    w = SCORE_WEIGHTS["small_charity"]
    factors["small_charity"] = _threshold_score(
        c.income, w["thresholds"], w["default"], comparison="lt"
    )

    # ── Late filing ──
    w = SCORE_WEIGHTS["late_filing"]
    if c.annual_returns:
        try:
            latest_str = c.annual_returns[0].fin_period_end[:10]
            latest_date = datetime.strptime(latest_str, "%Y-%m-%d")
            days_since = (datetime.now() - latest_date).days
            factors["late_filing"] = _threshold_score(
                days_since, w["thresholds"], w["default"], comparison="gt"
            )
        except (ValueError, TypeError):
            factors["late_filing"] = 0
    else:
        factors["late_filing"] = 0

    total = min(100, sum(factors.values()))
    c.need_score = NeedScore(total=total, factors=factors)


def _threshold_score(
    value: float,
    thresholds: List[tuple],
    default: int,
    comparison: str = "lt",
) -> int:
    """
    Walk a list of (threshold, points) and return the first match.

    comparison="lt": value < threshold → match  (for reserves, income trend)
    comparison="gt": value > threshold → match  (for spending ratio, days)
    """
    for threshold, points in thresholds:
        if comparison == "lt" and value < threshold:
            return points
        elif comparison == "gt" and value > threshold:
            return points
    return default


# ═══════════════════════════════════════════════════════════════════════════
# ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def _detect_anomalies(c: Charity) -> None:
    """
    Apply rule-based anomaly detection to a single charity.

    This is NOT fraud detection — it flags patterns that are
    "worth reviewing" for donors doing due diligence.
    """
    c.anomalies: List[Anomaly] = []

    for anomaly_type, rule in ANOMALY_RULES.items():
        field_name = rule["field"]
        value = getattr(c, field_name, None)

        if value is None:
            continue

        for condition in rule["conditions"]:
            threshold = condition["threshold"]
            operator = condition.get("operator", "lt")  # default: less-than
            severity = condition["severity"]
            template = condition["template"]

            triggered = False
            if operator == "lt" and value < threshold:
                triggered = True
            elif operator == "gt" and value > threshold:
                triggered = True

            if triggered:
                detail = template.format(
                    val=value,
                    pct=abs(value) * 100 if abs(value) < 100 else abs(value),
                )
                c.anomalies.append(
                    Anomaly(type=anomaly_type, severity=severity, detail=detail)
                )
                break  # Only the first (most severe) condition per rule


# ═══════════════════════════════════════════════════════════════════════════
# FILTERING
# ═══════════════════════════════════════════════════════════════════════════

def filter_viable_charities(charities: Dict[str, Charity]) -> List[Charity]:
    """
    Filter to charities that have enough data to be meaningfully scored.
    Returns a list sorted by need score (descending).
    """
    viable: List[Charity] = [
        c for c in charities.values()
        if (c.income > 0 or c.spending > 0) and c.postcode
    ]
    viable.sort(key=lambda c: c.need_score.total if c.need_score else 0, reverse=True)
    return viable
