#!/usr/bin/env python3
"""
Export nodes.json, edges.json, and baseline_predictions.json for the frontend.

Loads sahel_panel.parquet and spillover_graph.parquet, identifies latest year,
builds nodes (per-country metrics) and edges (from spillover graph), and baseline
predictions (no-shock model outputs). Saves to dataml/data/processed/.
Run from repo root: python -m dataml.scripts.export_baseline_structures
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

DATAML_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"

SAHEL_PANEL_PATH = PROCESSED_DIR / "sahel_panel.parquet"
SPILLOVER_GRAPH_PATH = PROCESSED_DIR / "spillover_graph.parquet"
NODES_JSON_PATH = PROCESSED_DIR / "nodes.json"
EDGES_JSON_PATH = PROCESSED_DIR / "edges.json"
BASELINE_PREDICTIONS_JSON_PATH = PROCESSED_DIR / "baseline_predictions.json"


def main() -> int:
    if not SAHEL_PANEL_PATH.exists():
        print(f"Error: Panel not found: {SAHEL_PANEL_PATH}. Run preprocess first.")
        return 1
    if not SPILLOVER_GRAPH_PATH.exists():
        print(f"Error: Graph not found: {SPILLOVER_GRAPH_PATH}. Run preprocess first.")
        return 1

    from dataml.src.simulate_aftershock import _get_baseline_predictions, _load_model_and_config, _load_panel_and_graph

    panel_df, graph_df = _load_panel_and_graph()
    baseline_year = int(panel_df["year"].max()) if len(panel_df) else 2024

    # Latest year rows
    latest = panel_df[panel_df["year"] == baseline_year]

    # nodes: one per country for latest year
    nodes = []
    for _, row in latest.iterrows():
        node = {
            "country": str(row["country_iso3"]),
            "year": int(row["year"]),
            "severity": round(float(row["severity"]), 2),
            "funding_total_usd": round(float(row["funding_total_usd"]), 0),
            "beneficiaries_total": int(row["beneficiaries_total"]),
            "funding_per_beneficiary": round(float(row["funding_per_beneficiary"]), 2),
            "underfunding_score": round(float(row["underfunding_score"]), 2),
            "chronic_underfunded_flag": int(row["chronic_underfunded_flag"]),
        }
        nodes.append(node)

    # edges: from spillover graph
    edges = []
    for _, row in graph_df.iterrows():
        edge = {
            "source_country": str(row["source_iso3"]),
            "target_country": str(row["target_iso3"]),
            "weight": round(float(row["weight"]), 2),
        }
        edges.append(edge)

    # baseline_predictions: no-shock model outputs
    model, config, node_to_idx = _load_model_and_config()
    baseline_predictions = _get_baseline_predictions(
        panel_df, graph_df, model, config, node_to_idx
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(NODES_JSON_PATH, "w") as f:
        json.dump(nodes, f, indent=2)
    with open(EDGES_JSON_PATH, "w") as f:
        json.dump(edges, f, indent=2)
    with open(BASELINE_PREDICTIONS_JSON_PATH, "w") as f:
        json.dump(baseline_predictions, f, indent=2)

    print(f"Exported {len(nodes)} nodes -> {NODES_JSON_PATH}")
    print(f"Exported {len(edges)} edges -> {EDGES_JSON_PATH}")
    print(f"Exported {len(baseline_predictions)} baseline predictions -> {BASELINE_PREDICTIONS_JSON_PATH}")
    return 0


if __name__ == "__main__":
    exit(main())
