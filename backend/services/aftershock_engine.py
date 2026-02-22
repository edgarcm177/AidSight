"""
Aftershock spillover simulation engine.
Deterministic graph propagation for funding adjustments and regional spillover.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

# Config constants for easy tuning
CONFIG = {
    "alpha": 0.35,   # severity sensitivity to stress
    "beta": 0.5,     # displaced sensitivity to stress
    "decay": 0.7,    # per-step propagation decay
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def simulate_aftershock(
    epicenter: str,
    delta_funding_pct: float,
    horizon_steps: int,
    data: Any,  # AftershockDataProvider duck type
    cost_per_person: float = 250.0,
    region_scope: Optional[List[str]] = None,
    debug: bool = False,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Run spillover simulation. Returns (result_dict, notes).
    """
    notes: List[str] = []
    year = data.get_baseline_year()
    panel = data.get_country_panel(year)
    edges_raw = data.get_edges()

    if epicenter not in panel:
        raise ValueError(f"Epicenter '{epicenter}' not in known countries: {list(panel.keys())}")

    # Build edge list (src -> [(dst, weight), ...])
    edge_map: Dict[str, List[Tuple[str, float]]] = {}
    for e in edges_raw:
        src = str(e.get("src", "")).upper()
        dst = str(e.get("dst", "")).upper()
        w = float(e.get("weight", 0.0))
        if src not in edge_map:
            edge_map[src] = []
        edge_map[src].append((dst, w))

    # Initial stress at epicenter
    ep = panel[epicenter]
    stress = -delta_funding_pct  # cuts increase stress
    coverage_proxy = ep.get("coverage_proxy", 0.5)
    severity0 = ep.get("severity", 0.5)
    displaced_out0 = ep.get("displaced_out", 10000)

    alpha = CONFIG["alpha"]
    beta = CONFIG["beta"]
    decay = CONFIG["decay"]

    delta_severity_epicenter = alpha * stress * (1 - coverage_proxy)
    delta_displaced_epicenter = beta * stress * (displaced_out0 / 100000.0) * 10000  # scale

    # Propagated shock per node: (delta_severity, delta_displaced)
    shock: Dict[str, Tuple[float, float]] = {}
    shock[epicenter] = (delta_severity_epicenter, delta_displaced_epicenter)

    # Propagate over steps
    edge_impacts: List[Dict[str, Any]] = []
    for step in range(horizon_steps - 1):
        next_shock: Dict[str, Tuple[float, float]] = {}
        for node, (ds, dd) in shock.items():
            for dst, weight in edge_map.get(node, []):
                if region_scope and dst not in region_scope:
                    continue
                prop_s = ds * weight * decay
                prop_d = dd * weight * decay
                edge_impacts.append({
                    "src": node, "dst": dst,
                    "weight": weight,
                    "propagated_displaced": prop_d,
                    "propagated_severity": prop_s,
                })
                if dst not in next_shock:
                    next_shock[dst] = (0.0, 0.0)
                os, od = next_shock[dst]
                next_shock[dst] = (os + prop_s, od + prop_d)
        # Merge into shock for next step
        for dst, (s, d) in next_shock.items():
            if dst not in shock:
                shock[dst] = (0.0, 0.0)
            cs, cd = shock[dst]
            shock[dst] = (cs + s, cd + d)

    # Build affected list (neighbors + epicenter)
    affected: List[Dict[str, Any]] = []
    total_displaced = 0.0
    total_cost = 0.0
    max_delta_severity = 0.0

    all_affected = set(shock.keys())
    for country in all_affected:
        if country not in panel:
            continue
        if region_scope and country not in region_scope:
            continue
        ds, dd = shock[country]
        total_displaced += dd
        extra_cost = dd * cost_per_person
        total_cost += extra_cost
        max_delta_severity = max(max_delta_severity, abs(ds))

        p_row = panel[country]
        funding_proxy = p_row.get("funding_usd", 1e8) / 1e8
        sev = p_row.get("severity", 0.5) + ds
        # prob_underfunded_next = sigmoid(a*severity - b*funding_proxy)
        prob = _sigmoid(3.0 * sev - 2.0 * funding_proxy)
        prob = _clamp(prob, 0.0, 1.0)

        expl = f"Spillover from epicenter" if country != epicenter else "Direct funding impact"
        affected.append({
            "country": country,
            "delta_severity": round(ds, 4),
            "delta_displaced": round(dd, 2),
            "extra_cost_usd": round(extra_cost, 2),
            "prob_underfunded_next": round(prob, 4),
            "explanation": expl,
        })

    totals = {
        "total_delta_displaced": round(total_displaced, 2),
        "total_extra_cost_usd": round(total_cost, 2),
        "affected_countries": len(affected),
        "max_delta_severity": round(max_delta_severity, 4),
    }

    result = {
        "baseline_year": year,
        "epicenter": epicenter,
        "delta_funding_pct": delta_funding_pct,
        "horizon_steps": horizon_steps,
        "affected": affected,
        "totals": totals,
        "graph_edges_used": edge_impacts if debug and edge_impacts else None,
        "notes": notes,
    }
    return result, notes
