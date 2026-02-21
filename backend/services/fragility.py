from typing import Dict, Any
import pandas as pd

from .scenarios import apply_scenario_to_crisis


def compute_ttc(row: pd.Series) -> float:
    """
    Time to Collapse (days) – placeholder formula.
    Replace with something based on severity, coverage, etc.
    """
    severity = row.get("severity", 1.0)
    coverage = row.get("coverage", 0.0)
    return max(1.0, (coverage * 100.0) / severity)


def compute_equity_shift(baseline_df: pd.DataFrame, scenario_df: pd.DataFrame) -> float:
    """
    Equity Shift % – how much funding moved from overserved to underserved.
    Placeholder: return 0 for now.
    """
    return 0.0


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

    metrics = {
        "baseline_ttc_days": baseline_ttc,
        "scenario_ttc_days": scenario_ttc,
        "baseline_equity_shift_pct": 0.0,
        "scenario_equity_shift_pct": 0.0,
        "at_risk_population": int(crisis_row.get("people_in_need", 0)),
    }

    impacted_regions = [
        {
            "region": crisis_row.get("region", crisis_row.get("country", "Unknown")),
            "delta_ttc_days": scenario_ttc - baseline_ttc,
            "funding_gap_usd": float(
                crisis_row.get("funding_required", 0.0)
                - crisis_row.get("funding_received", 0.0)
            ),
        }
    ]

    return {"crisis_id": crisis_id, "metrics": metrics, "impacted_regions": impacted_regions}
