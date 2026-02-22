"""
Internal smoke test helper for Data & ML layer.
Call from REPL or unit tests: run_data_ml_smoketest(), run_aftershock_smoketest()
"""

import logging
from typing import Any, Dict

from fastapi.testclient import TestClient

from ..data import data_loader
from ..main import app
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

    try:
        sim = run_fragility_simulation(crises_df, scenario_negative)
        result["simulate_ok"] = True
        result["sample_ttc_baseline"] = sim["metrics"]["baseline_ttc_days"]
        result["sample_ttc_scenario"] = sim["metrics"]["scenario_ttc_days"]
        result["sample_equity_shift"] = sim["metrics"]["scenario_equity_shift_pct"]
    except Exception as e:
        log.warning("Smoketest: run_fragility_simulation failed: %s", e)
        result["simulate_ok"] = False

    try:
        crisis_row = crises_df.loc[crises_df["id"] == crisis_id].iloc[0]
        crisis_dict = crisis_row.to_dict()
        sim = run_fragility_simulation(crises_df, scenario_positive)
        memo = build_contrarian_memo(crisis_dict, sim, twin=None)
        result["memo_ok"] = bool(memo and "title" in memo and "body" in memo)
    except Exception as e:
        log.warning("Smoketest: build_contrarian_memo failed: %s", e)
        result["memo_ok"] = False

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


def run_aftershock_smoketest() -> Dict[str, Any]:
    """
    Smoke test Aftershock endpoints via TestClient.
    Covers POST /simulate/shock, GET /crises/nodes, /edges, /baseline_predictions,
    GET /projects/metrics, GET /projects/neighbors/{project_id}.
    """
    result: Dict[str, Any] = {
        "simulate_shock_ok": False,
        "crises_nodes_ok": False,
        "crises_edges_ok": False,
        "crises_baseline_ok": False,
        "projects_metrics_ok": False,
        "projects_neighbors_ok": False,
    }
    client = TestClient(app)

    # POST /simulate/shock
    try:
        r = client.post(
            "/simulate/shock",
            json={"country": "BFA", "delta_funding_pct": -0.2, "horizon_steps": 2},
        )
        if r.status_code == 200:
            data = r.json()
            expected = {"baseline_year", "epicenter", "affected", "total_extra_displaced", "total_extra_cost_usd", "notes"}
            result["simulate_shock_ok"] = expected.issubset(set(data.keys()))
        else:
            log.warning("Smoketest: /simulate/shock returned %s", r.status_code)
    except Exception as e:
        log.warning("Smoketest: /simulate/shock failed: %s", e)

    # GET /crises/nodes
    try:
        r = client.get("/crises/nodes")
        if r.status_code == 200:
            data = r.json()
            result["crises_nodes_ok"] = isinstance(data, list) and len(data) > 0
            if result["crises_nodes_ok"] and data:
                result["crises_nodes_ok"] = "country" in data[0] and "severity" in data[0]
        else:
            result["crises_nodes_ok"] = False
    except Exception as e:
        log.warning("Smoketest: /crises/nodes failed: %s", e)

    # GET /crises/edges
    try:
        r = client.get("/crises/edges")
        if r.status_code == 200:
            data = r.json()
            result["crises_edges_ok"] = isinstance(data, list) and len(data) > 0
            if result["crises_edges_ok"] and data:
                e0 = data[0]
                result["crises_edges_ok"] = ("source_country" in e0 or "src" in e0) and ("target_country" in e0 or "dst" in e0)
        else:
            result["crises_edges_ok"] = False
    except Exception as e:
        log.warning("Smoketest: /crises/edges failed: %s", e)

    # GET /crises/baseline_predictions
    try:
        r = client.get("/crises/baseline_predictions")
        if r.status_code == 200:
            data = r.json()
            result["crises_baseline_ok"] = isinstance(data, list) and len(data) > 0
        else:
            result["crises_baseline_ok"] = False
    except Exception as e:
        log.warning("Smoketest: /crises/baseline_predictions failed: %s", e)

    # GET /projects/metrics
    try:
        r = client.get("/projects/metrics")
        if r.status_code == 200:
            data = r.json()
            result["projects_metrics_ok"] = isinstance(data, list) and len(data) > 0
        else:
            result["projects_metrics_ok"] = False
    except Exception as e:
        log.warning("Smoketest: /projects/metrics failed: %s", e)

    # GET /projects/neighbors/{project_id}
    try:
        r = client.get("/projects/neighbors/P00000")
        if r.status_code == 200:
            data = r.json()
            result["projects_neighbors_ok"] = "project_id" in data and "neighbors" in data
        else:
            result["projects_neighbors_ok"] = False
    except Exception as e:
        log.warning("Smoketest: /projects/neighbors failed: %s", e)

    return result
