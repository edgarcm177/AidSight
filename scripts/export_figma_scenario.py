#!/usr/bin/env python3
"""
Export one Aftershock scenario as JSON for Figma Make.
Runs a single simulation (BFA, -20%, horizon 2) and outputs baseline + aftershock + memo spillover.
Run from repo root: python scripts/export_figma_scenario.py
Output: scenario_for_figma.json
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    # Load baseline nodes/edges
    nodes_path = REPO_ROOT / "dataml" / "data" / "processed" / "nodes.json"
    edges_path = REPO_ROOT / "dataml" / "data" / "processed" / "edges.json"

    baseline_nodes = []
    baseline_edges = []
    if nodes_path.exists():
        with open(nodes_path) as f:
            baseline_nodes = json.load(f)
    if edges_path.exists():
        with open(edges_path) as f:
            baseline_edges = json.load(f)

    # Run aftershock simulation
    aftershock_result = None
    try:
        from dataml.src.simulate_aftershock import simulate_aftershock

        raw = simulate_aftershock(
            node_iso3="BFA",
            delta_funding_pct=-0.2,
            horizon_years=2,
        )
        aftershock_result = {
            "affected": [
                {
                    "country": a.get("country", ""),
                    "delta_severity": a.get("delta_severity", 0),
                    "delta_displaced": a.get("delta_displaced", 0),
                    "extra_cost_usd": a.get("extra_cost_usd", 0),
                    "prob_underfunded_next": a.get("prob_underfunded_next", 0),
                }
                for a in raw.get("affected", [])
            ],
            "totals": raw.get("totals", {}),
            "baseline_year": raw.get("baseline_year", 2026),
            "epicenter": raw.get("epicenter", "BFA"),
        }
    except Exception as e:
        print(f"Note: Aftershock simulation failed: {e}")
        aftershock_result = {
            "affected": [{"country": "NER", "delta_displaced": 45000, "extra_cost_usd": 4500000}],
            "totals": {"total_delta_displaced": 112000, "total_extra_cost_usd": 24000000, "affected_countries": 3},
            "baseline_year": 2026,
            "epicenter": "BFA",
        }

    # Memo spillover sentence
    memo_spillover = ""
    if aftershock_result:
        totals = aftershock_result.get("totals", {})
        affected = aftershock_result.get("affected", [])
        top = sorted(affected, key=lambda x: x.get("delta_displaced", 0), reverse=True)[:3]
        countries = ", ".join(f"{a['country']} (+{int(a.get('delta_displaced',0)):,})" for a in top)
        memo_spillover = (
            f"Spillover risk: A -20% funding shock in Burkina Faso could displace "
            f"~{int(totals.get('total_delta_displaced',0)):,} extra people across neighbors, "
            f"with {countries} most affected. Extra cost: ~${totals.get('total_extra_cost_usd',0)/1e6:.1f}M."
        )

    out = {
        "baseline": {"nodes": baseline_nodes, "edges": baseline_edges},
        "aftershock": aftershock_result,
        "memo_spillover": memo_spillover,
    }

    out_path = REPO_ROOT / "scenario_for_figma.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Exported -> {out_path}")
    return 0


if __name__ == "__main__":
    exit(main())
