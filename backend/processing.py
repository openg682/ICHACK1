"""
Charity Intelligence Map — Processing Engine (Cluster-Stretch v5)
================================================================
Computes need scores and detects anomalies for each charity using
factor-level percentile scoring and adaptive cluster stretching.

Features:
- Factor-level percentiles to spread the main cluster
- Total scores rescaled to ~50–85 for main cluster
- Extreme outliers can exceed 85 up to 100
- Minimum spending filter applied before scoring
- Keeps anomaly detection intact
"""

from datetime import datetime
from backend.config import SCORE_WEIGHTS, ANOMALY_RULES, DEFAULT_MIN_SPENDING
from backend.models import Charity, NeedScore, Anomaly


# ──────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────

def compute_need_scores(charities: dict[str, Charity]) -> None:
    """
    Compute need scores for all charities (mutates in-place).

    Steps:
    1. Apply min-spending filter
    2. Compute derived metrics
    3. Assign factor-level percentile scores
    4. Sum factor scores into total and adaptively rescale
    5. Detect anomalies
    """
    # Step 0: Apply min-spending filter
    filtered = {cid: c for cid, c in charities.items() if c.spending >= DEFAULT_MIN_SPENDING}

    if not filtered:
        return

    # Step 1: Compute derived metrics
    for c in filtered.values():
        _compute_derived_metrics(c)

    # Step 2: Collect factor values for percentile calculation
    factor_values = {key: [] for key in SCORE_WEIGHTS.keys()}
    for c in filtered.values():
        for factor, cfg in SCORE_WEIGHTS.items():
            value = _extract_factor_value(c, factor)
            if value is not None:
                factor_values[factor].append(value)

    # Compute sorted values per factor
    factor_percentiles = {f: sorted(vals) for f, vals in factor_values.items()}

    # Step 3: Assign raw factor scores
    raw_totals = []
    for c in filtered.values():
        factors = {}
        for factor, cfg in SCORE_WEIGHTS.items():
            value = _extract_factor_value(c, factor)
            if value is not None and factor_percentiles[factor]:
                score = _factor_percentile_score(value, factor, factor_percentiles[factor], cfg)
            else:
                score = 0
            factors[factor] = score
        c.need_score = NeedScore(total=sum(factors.values()), factors=factors)
        raw_totals.append(c.need_score.total)

    # Step 4: Adaptive cluster stretching
    if raw_totals:
        min_raw = min(raw_totals)
        max_raw = max(raw_totals)
        cluster_min = 50
        cluster_max = 85

        for c in filtered.values():
            # Scale raw total to cluster range
            if max_raw != min_raw:
                scaled = cluster_min + (c.need_score.total - min_raw) / (max_raw - min_raw) * (cluster_max - cluster_min)
            else:
                scaled = cluster_min
            # Cap extreme outliers at 100
            c.need_score.total = round(min(100, scaled))

            _detect_anomalies(c)

    # Step 5: Replace original dict with filtered charities
    charities.clear()
    charities.update(filtered)


# ──────────────────────────────────────────────────────────────
# DERIVED METRICS
# ──────────────────────────────────────────────────────────────

def _compute_derived_metrics(c: Charity) -> None:
    """Compute intermediate financial metrics for scoring and anomalies."""
    c.annual_returns.sort(key=lambda ar: ar.fin_period_end, reverse=True)

    c.reserves_months = round((c.reserves / c.spending) * 12, 1) if c.spending > 0 and c.reserves >= 0 else None

    if len(c.annual_returns) >= 2:
        latest = c.annual_returns[0].income
        previous = c.annual_returns[1].income
        c.income_trend = round((latest - previous) / previous, 3) if previous > 0 else None
    else:
        c.income_trend = None

    c.spending_ratio = round(c.spending / c.income, 3) if c.income > 0 else None


# ──────────────────────────────────────────────────────────────
# FACTOR EXTRACTION
# ──────────────────────────────────────────────────────────────

def _extract_factor_value(c: Charity, factor: str):
    if factor == "low_reserves":
        return c.reserves_months
    elif factor == "income_declining":
        return c.income_trend
    elif factor == "overspending":
        return c.spending_ratio
    elif factor == "small_charity":
        return c.income
    elif factor == "late_filing":
        if c.annual_returns:
            try:
                latest_str = c.annual_returns[0].fin_period_end[:10]
                latest_date = datetime.strptime(latest_str, "%Y-%m-%d")
                return (datetime.now() - latest_date).days
            except (ValueError, TypeError):
                return None
        return None
    elif factor == "multi_year_decline":
        return _count_declining_years(c)
    return None


# ──────────────────────────────────────────────────────────────
# FACTOR SCORING USING PERCENTILES
# ──────────────────────────────────────────────────────────────

def _factor_percentile_score(value, factor, all_values, cfg):
    low, high = cfg["range"]
    max_points = cfg["max"]
    direction = cfg["direction"]

    clamped = max(low, min(high, value))
    if direction == "lower_is_worse":
        percentile = (high - clamped) / (high - low)
    else:
        percentile = (clamped - low) / (high - low)

    return round(max_points * percentile)


# ──────────────────────────────────────────────────────────────
# MULTI-YEAR DECLINE
# ──────────────────────────────────────────────────────────────

def _count_declining_years(c: Charity) -> int:
    if len(c.annual_returns) < 2:
        return 0
    declining = 0
    for i in range(len(c.annual_returns) - 1):
        if c.annual_returns[i].income < c.annual_returns[i + 1].income:
            declining += 1
        else:
            break
    return declining


# ──────────────────────────────────────────────────────────────
# ANOMALY DETECTION
# ──────────────────────────────────────────────────────────────

def _detect_anomalies(c: Charity) -> None:
    c.anomalies = []
    for anomaly_type, rule in ANOMALY_RULES.items():
        field_name = rule["field"]
        value = getattr(c, field_name, None)
        if value is None:
            continue
        for condition in rule["conditions"]:
            threshold = condition["threshold"]
            operator = condition.get("operator", "lt")
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
                c.anomalies.append(Anomaly(type=anomaly_type, severity=severity, detail=detail))
                break


# ──────────────────────────────────────────────────────────────
# FILTERED LIST OUTPUT
# ──────────────────────────────────────────────────────────────

def filter_viable_charities(charities: dict[str, Charity]) -> list[Charity]:
    viable = [c for c in charities.values()
              if c.spending >= DEFAULT_MIN_SPENDING and (c.income > 0 or c.spending > 0) and c.postcode]
    viable.sort(key=lambda c: c.need_score.total if c.need_score else 0, reverse=True)
    return viable
