from typing import Dict, Any
import pandas as pd


def apply_scenario_to_crisis(
    crisis_row: pd.Series,
    scenario_input: Dict[str, Any],
) -> pd.Series:
    """
    Apply funding changes and shocks to a single crisis row.
    Returns a modified copy of the row.
    """
    row = crisis_row.copy()

    shock = scenario_input.get("shock", {})
    funding_changes = scenario_input.get("funding_changes", [])

    # Example: simple inflation impact on effective coverage
    inflation_pct = shock.get("inflation_pct", 0.0)
    coverage = row.get("coverage", 0.0)
    row["coverage"] = max(0.0, coverage - inflation_pct / 200.0)

    # Example: adjust funding_received by sum of deltas
    delta_total = sum(fc.get("delta_usd", 0.0) for fc in funding_changes)
    row["funding_received"] = row.get("funding_received", 0.0) + delta_total

    return row
