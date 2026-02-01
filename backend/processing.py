"""
Charity Intelligence Map — Processing Engine (v2)
===================================================
Computes need scores and detects anomalies for each charity.

V2 changes from V1:
  - Continuous interpolation instead of step-function thresholds
  - Tighter thresholds (6-month reserves is normal, not a red flag)
  - Percentile normalization so scores spread across the full 0-100 range
  - New "multi_year_decline" factor for sustained downward trends
  - Small charity factor dramatically reduced (being small ≠ high need)

The result is a score where:
  - Top ~10% of charities are "critical" (75+)
  - Next ~15% are "high need" (50-74)
  - Middle ~35% are "medium" (25-49)
  - Bottom ~40% are "low" (0-24)
"""

from datetime import datetime

from backend.config import SCORE_WEIGHTS, SCORE_NORMALIZATION, ANOMALY_RULES
from backend.models import Charity, NeedScore, Anomaly


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def compute_need_scores(charities: dict[str, Charity]) -> None:
    """
    Compute need scores for all charities (mutates in-place).

    Two-pass process:
      1. Compute raw factor scores using continuous interpolation
      2. Normalize to percentiles so scores spread across 0-100
    """
    # Pass 1: derive metrics and compute raw scores
    for c in charities.values():
        _compute_derived_metrics(c)
        _compute_raw_score(c)
        _detect_anomalies(c)

    # Pass 2: percentile normalization
    if SCORE_NORMALIZATION.get("enabled", True):
        _normalize_scores(charities)


# ═══════════════════════════════════════════════════════════════════════════
# DERIVED METRICS
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# RAW SCORE COMPUTATION (continuous interpolation)
# ═══════════════════════════════════════════════════════════════════════════

def _compute_raw_score(c: Charity) -> None:
    """
    Compute raw need score using continuous interpolation.

    Instead of step functions (value < X → Y points), each factor
    smoothly interpolates between 0 and max_points based on where
    the value falls within the configured range.
    """
    factors: dict[str, int] = {}

    # ── Low reserves ──
    w = SCORE_WEIGHTS["low_reserves"]
    if c.reserves_months is not None:
        factors["low_reserves"] = _interpolate(
            c.reserves_months, w["range"], w["max"], w["direction"]
        )
    else:
        factors["low_reserves"] = 0

    # ── Income declining ──
    w = SCORE_WEIGHTS["income_declining"]
    if c.income_trend is not None:
        factors["income_declining"] = _interpolate(
            c.income_trend, w["range"], w["max"], w["direction"]
        )
    else:
        factors["income_declining"] = 0

    # ── Overspending ──
    w = SCORE_WEIGHTS["overspending"]
    if c.spending_ratio is not None:
        factors["overspending"] = _interpolate(
            c.spending_ratio, w["range"], w["max"], w["direction"]
        )
    else:
        factors["overspending"] = 0

    # ── Small charity ──
    w = SCORE_WEIGHTS["small_charity"]
    factors["small_charity"] = _interpolate(
        c.income, w["range"], w["max"], w["direction"]
    )

    # ── Late filing ──
    w = SCORE_WEIGHTS["late_filing"]
    if c.annual_returns:
        try:
            latest_str = c.annual_returns[0].fin_period_end[:10]
            latest_date = datetime.strptime(latest_str, "%Y-%m-%d")
            days_since = (datetime.now() - latest_date).days
            factors["late_filing"] = _interpolate(
                days_since, w["range"], w["max"], w["direction"]
            )
        except (ValueError, TypeError):
            factors["late_filing"] = 0
    else:
        factors["late_filing"] = 0

    # ── Multi-year decline (NEW) ──
    w = SCORE_WEIGHTS["multi_year_decline"]
    declining_years = _count_declining_years(c)
    factors["multi_year_decline"] = _interpolate(
        declining_years, w["range"], w["max"], w["direction"]
    )

    total = min(100, sum(factors.values()))
    c.need_score = NeedScore(total=total, factors=factors)


def _interpolate(value: float, range_: tuple, max_points: int, direction: str) -> int:
    """
    Continuously interpolate a value within a range to 0–max_points.

    For "lower_is_worse":  value ≤ range[0] → max_points, value ≥ range[1] → 0
    For "higher_is_worse": value ≥ range[1] → max_points, value ≤ range[0] → 0
    """
    low, high = range_

    if direction == "lower_is_worse":
        # e.g. reserves: lower reserves = more points
        if value <= low:
            return max_points
        if value >= high:
            return 0
        # Linear interpolation: as value goes from high→low, score goes 0→max
        fraction = (high - value) / (high - low)
        return round(max_points * fraction)

    else:  # higher_is_worse
        # e.g. spending ratio: higher ratio = more points
        if value >= high:
            return max_points
        if value <= low:
            return 0
        # Linear interpolation: as value goes from low→high, score goes 0→max
        fraction = (value - low) / (high - low)
        return round(max_points * fraction)


def _count_declining_years(c: Charity) -> int:
    """Count how many consecutive recent years show income decline."""
    if len(c.annual_returns) < 2:
        return 0

    declining = 0
    for i in range(len(c.annual_returns) - 1):
        if c.annual_returns[i].income < c.annual_returns[i + 1].income:
            declining += 1
        else:
            break  # Stop at first non-declining year
    return declining


# ═══════════════════════════════════════════════════════════════════════════
# PERCENTILE NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_scores(charities: dict[str, Charity]) -> None:
    """
    Normalize raw scores to percentiles so the final 0-100 score
    is always well-distributed, regardless of how many charities
    trigger each factor.

    After this, a score of 75 means "in the top 25% of need"
    relative to the dataset — not an absolute measure.
    """
    # Collect charities that have scores
    scored = [c for c in charities.values() if c.need_score is not None]
    if len(scored) < 10:
        return  # Too few to normalize meaningfully

    # Sort by raw score ascending
    scored.sort(key=lambda c: c.need_score.total)

    n = len(scored)
    for rank, c in enumerate(scored):
        # Percentile: what fraction of charities have a lower raw score
        percentile = rank / n  # 0.0 to ~1.0

        # Map percentile to 0-100 final score
        # Apply a slight S-curve to push extremes apart
        normalized = _s_curve(percentile) * 100

        # Store the raw score in factors for transparency
        c.need_score.factors["_raw_total"] = c.need_score.total
        c.need_score.total = round(normalized)


def _s_curve(x: float) -> float:
    """
    Piecewise linear percentile-to-score mapping.

    Controls exactly what fraction of charities land in each band:
      Bottom 45% of raw scores → scores 0-24   (Low / teal markers)
      Next   30%               → scores 25-49  (Medium / amber)
      Next   15%               → scores 50-74  (High / coral)
      Top    10%               → scores 75-100 (Critical / red)

    This means on the map, ~45% of markers will be teal, ~30% amber,
    ~15% coral, and only ~10% red — giving a clear visual hierarchy.
    """
    # (percentile_breakpoint, score_breakpoint)
    breakpoints = [
        (0.00,  0),
        (0.45, 25),
        (0.75, 50),
        (0.90, 75),
        (1.00, 100),
    ]

    # Find which segment x falls in
    for i in range(len(breakpoints) - 1):
        x0, y0 = breakpoints[i]
        x1, y1 = breakpoints[i + 1]
        if x <= x1:
            # Linear interpolation within this segment
            t = (x - x0) / (x1 - x0) if x1 > x0 else 0
            return (y0 + t * (y1 - y0)) / 100.0

    return 1.0


# ═══════════════════════════════════════════════════════════════════════════
# ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def _detect_anomalies(c: Charity) -> None:
    """
    Apply rule-based anomaly detection to a single charity.

    This is NOT fraud detection — it flags patterns that are
    "worth reviewing" for donors doing due diligence.
    """
    c.anomalies = []

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

def filter_viable_charities(charities: dict[str, Charity]) -> list[Charity]:
    """
    Filter to charities that have enough data to be meaningfully scored.
    Returns a list sorted by need score (descending).
    """
    viable = [
        c for c in charities.values()
        if (c.income > 0 or c.spending > 0) and c.postcode
    ]
    viable.sort(key=lambda c: c.need_score.total if c.need_score else 0, reverse=True)
    return viable