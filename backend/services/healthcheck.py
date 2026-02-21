"""
Internal smoke test helper for Data & ML layer.
Call from REPL or unit tests: run_data_ml_smoketest()
"""

import logging
from typing import Any, Dict

from ..data import data_loader
from .fragility import run_fragility_simulation
from .memo import build_contrarian_memo
from .twins import find_success_twin

log = logging.getLogger(__name__)


def run_data_ml_smoketest() -> Dict[str, Any]:
    """
    Run a minimal smoke test on crises, projects, simulate, memo, and twins.
    Returns high-level booleans and sample numbers; catches exceptions.
    """
    result: Dict[str, Any] = {
        "crises_present": False,
        "projects_present": False,
        "simulate_ok": False,
        "memo_ok": False,
        "twins_ok": False,
        "sample_ttc_baseline": None,
        "sample_ttc_scenario": None,
        "sample_equity_shift": None,
    }

    # Load data
    try:
        crises_df = data_loader.load_crises()
        projects_df = data_loader.load_projects()
    except Exception as e:
        log.warning("Smoketest: failed to load data: %s", e)
        return result

    if len(crises_df) == 0:
        log.warning("Smoketest: crises table is empty")
        return result
    result["crises_present"] = True

    if len(projects_df) == 0:
        log.warning("Smoketest: projects table is empty")
        return result
    result["projects_present"] = True

    crisis_id = str(crises_df["id"].iloc[0])
    project_id = str(projects_df["id"].iloc[0])

    # Simple scenarios: small negative and small positive funding shock
    scenario_negative = {
        "crisis_id": crisis_id,
        "funding_changes": [{"sector": "Health", "delta_usd": -1_000_000}],
        "shock": {"inflation_pct": 0.0, "drought": False, "conflict_intensity": 0.0},
    }
    scenario_positive = {
        "crisis_id": crisis_id,
        "funding_changes": [{"sector": "Health", "delta_usd": 500_000}],
        "shock": {"inflation_pct": 0.0, "drought": False, "conflict_intensity": 0.0},
    }

    # Run simulate (use negative shock)
    try:
        sim = run_fragility_simulation(crises_df, scenario_negative)
        result["simulate_ok"] = True
        result["sample_ttc_baseline"] = sim["metrics"]["baseline_ttc_days"]
        result["sample_ttc_scenario"] = sim["metrics"]["scenario_ttc_days"]
        result["sample_equity_shift"] = sim["metrics"]["scenario_equity_shift_pct"]
    except Exception as e:
        log.warning("Smoketest: run_fragility_simulation failed: %s", e)
        result["simulate_ok"] = False

    # Run memo (with simulation; optional twin)
    try:
        crisis_row = crises_df.loc[crises_df["id"] == crisis_id].iloc[0]
        crisis_dict = crisis_row.to_dict()
        sim = run_fragility_simulation(crises_df, scenario_positive)
        memo = build_contrarian_memo(crisis_dict, sim, twin=None, scenario=None)
        if memo and "title" in memo and "body" in memo:
            result["memo_ok"] = True
        else:
            result["memo_ok"] = False
    except Exception as e:
        log.warning("Smoketest: build_contrarian_memo failed: %s", e)
        result["memo_ok"] = False

    # Run memo with twin
    try:
        twin = find_success_twin(projects_df, project_id)
        crisis_row = crises_df.loc[crises_df["id"] == crisis_id].iloc[0]
        crisis_dict = crisis_row.to_dict()
        sim = run_fragility_simulation(crises_df, scenario_positive)
        memo = build_contrarian_memo(crisis_dict, sim, twin=twin, scenario=None)
        if memo and "title" in memo:
            result["memo_ok"] = result["memo_ok"] or True
    except Exception as e:
        log.warning("Smoketest: build_contrarian_memo with twin failed: %s", e)

    # Run twins
    try:
        twin = find_success_twin(projects_df, project_id)
        if twin and "twin_project_id" in twin and "similarity_score" in twin:
            result["twins_ok"] = True
        else:
            result["twins_ok"] = False
    except Exception as e:
        log.warning("Smoketest: find_success_twin failed: %s", e)
        result["twins_ok"] = False

    return result
