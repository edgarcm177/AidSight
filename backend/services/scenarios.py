from typing import Dict, Any
import math
import pandas as pd


def _safe_coverage(val: float) -> float:
    """Ensure coverage in [0, 1]; NaN/Inf → 0."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return 0.0
    v = float(val)
    return max(0.0, min(1.0, v))


def apply_scenario_to_crisis(
    crisis_row: pd.Series,
    scenario_input: Dict[str, Any],
) -> pd.Series:
    """
    Apply funding changes and shocks to a single crisis row.
    Returns a modified copy with updated funding_received, coverage, and severity.

    Expects row with: funding_required, funding_received, coverage, severity.
    Transforms:
      1. funding_received += sum(delta_usd) from funding_changes
      2. coverage = funding_received / funding_required (0 if denom ≤ 0), clipped
      3. Inflation: coverage -= inflation_pct/200
      4. Drought: severity *= 1.1 (cap at 5.0)
      5. Conflict: coverage -= 0.2 * conflict_intensity
    """
    row = crisis_row.copy()

    shock = scenario_input.get("shock", {})
    funding_changes = scenario_input.get("funding_changes", [])

    # 1. Apply funding deltas (funding_required unchanged)
    delta_total = sum(fc.get("delta_usd", 0.0) for fc in funding_changes)
    row["funding_received"] = float(row.get("funding_received", 0.0)) + delta_total

    # 2. Recompute coverage from funding_received / funding_required
    funding_required = float(row.get("funding_required", 0.0))
    if funding_required > 0:
        coverage = float(row["funding_received"]) / funding_required
    else:
        coverage = 0.0
    row["coverage"] = _safe_coverage(coverage)

    # 3. Inflation: reduce effective coverage per % inflation
    inflation_pct = float(shock.get("inflation_pct", 0.0))
    row["coverage"] = _safe_coverage(row["coverage"] - inflation_pct / 200.0)

    # 4. Drought: increase severity slightly
    severity = float(row.get("severity", 1.0))
    if shock.get("drought", False):
        severity = severity * 1.1
    row["severity"] = min(5.0, max(1.0, severity))

    # 5. Conflict intensity (0–1): reduce coverage
    conflict_intensity = float(shock.get("conflict_intensity", 0.0))
    conflict_intensity = max(0.0, min(1.0, conflict_intensity))
    row["coverage"] = _safe_coverage(row["coverage"] - 0.2 * conflict_intensity)

    return row
