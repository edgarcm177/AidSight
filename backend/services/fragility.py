from typing import Dict, Any
import math
import pandas as pd

from .scenarios import apply_scenario_to_crisis


def _safe_coverage(val: float) -> float:
    """Ensure coverage is in [0, 1]; NaN/Inf → 0."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return 0.0
    v = float(val)
    return max(0.0, min(1.0, v))


def compute_ttc(row: pd.Series) -> float:
    """
    Time to Collapse (TTC) in days, from severity and coverage.

    How to interpret: TTC = estimated days until system collapse under stress.
    Higher TTC = more resilient (system holds longer).
    Lower TTC = more fragile (collapse sooner).
    In the app, compare baseline vs scenario TTC to see if your strategy improves resilience.

    Expects row with: severity (≥ 1.0), coverage (0–1).
    Formula: ttc = max(1.0, (coverage * 180.0) / severity)
    Guard: coverage clamped to [0, 1]; NaN/Inf treated as 0.
    """
    severity = float(row.get("severity", 1.0))
    coverage = _safe_coverage(row.get("coverage", 0.0))
    severity = max(1.0, severity)
    return max(1.0, (coverage * 180.0) / severity)


def compute_equity_shift(baseline_row: pd.Series, scenario_row: pd.Series) -> float:
    """
    Equity Shift % for a single crisis: gap shrinkage when coverage improves.

    How to interpret: gap = 1 - coverage (higher gap = more underserved).
    equity_shift_pct = (gap0 - gap1) * 100, i.e. percentage-point change in coverage.
    Positive = improved coverage (better equity).
    Negative = coverage regression (worse equity).
    In the app, use this to see if funding moves toward high-need regions.

    Treats the selected crisis as the only one that changes.
    Guard: coverage always in [0, 1]; NaN/Inf treated as 0.
    """
    c0 = _safe_coverage(baseline_row.get("coverage", 0.0))
    c1 = _safe_coverage(scenario_row.get("coverage", 0.0))
    gap0 = 1.0 - c0
    gap1 = 1.0 - c1
    return (gap0 - gap1) * 100.0


def run_fragility_simulation(
    crises_df: pd.DataFrame,
    scenario_input: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Given global crises_df and scenario_input dict,
    return dict with metrics + impacted regions for that crisis.
    """
    crisis_id = scenario_input["crisis_id"]
    crisis_row = crises_df.loc[crises_df["id"] == crisis_id].iloc[0]

    baseline_ttc = compute_ttc(crisis_row)

    scenario_row = apply_scenario_to_crisis(crisis_row, scenario_input)
    scenario_ttc = compute_ttc(scenario_row)

    # Equity shift: baseline is 0 by definition; scenario uses coverage change
    scenario_equity_shift = compute_equity_shift(crisis_row, scenario_row)

    metrics = {
        "baseline_ttc_days": baseline_ttc,
        "scenario_ttc_days": scenario_ttc,
        "baseline_equity_shift_pct": 0.0,
        "scenario_equity_shift_pct": scenario_equity_shift,
        "at_risk_population": int(crisis_row.get("people_in_need", 0)),
    }

    funding_required = float(crisis_row.get("funding_required", 0.0))
    funding_received = float(crisis_row.get("funding_received", 0.0))
    funding_gap_usd = funding_required - funding_received

    impacted_regions = [
        {
            "region": crisis_row.get("region", crisis_row.get("country", "Unknown")),
            "delta_ttc_days": scenario_ttc - baseline_ttc,
            "funding_gap_usd": funding_gap_usd,
        }
    ]

    return {"crisis_id": crisis_id, "metrics": metrics, "impacted_regions": impacted_regions}
