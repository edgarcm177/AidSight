"""
Main simulation API for Aftershock.

Loads trained model and processed data; runs simulate_aftershock(node_iso3, delta_funding_pct, horizon_years)
and returns a structured dict/JSON for Backend to wrap.

Backend calls: from dataml.src.simulate_aftershock import simulate_aftershock
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import torch

from .graph import get_edge_index, get_node_to_idx
from .train import SpilloverGNN

# Paths relative to dataml/ (parent of src/)
DATAML_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"
MODELS_DIR = DATAML_ROOT / "models"

SAHEL_PANEL_PATH = PROCESSED_DIR / "sahel_panel.parquet"
SPILLOVER_GRAPH_PATH = PROCESSED_DIR / "spillover_graph.parquet"
MODEL_PATH = MODELS_DIR / "spillover_model.pt"
CONFIG_PATH = MODELS_DIR / "model_config.json"


def _load_model_and_data() -> tuple:
    """Load model, config, panel, graph. Raises FileNotFoundError if missing."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}. Run dataml train first.")
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}. Run dataml train first.")
    if not SAHEL_PANEL_PATH.exists():
        raise FileNotFoundError(f"Panel not found: {SAHEL_PANEL_PATH}. Run dataml preprocess first.")
    if not SPILLOVER_GRAPH_PATH.exists():
        raise FileNotFoundError(f"Graph not found: {SPILLOVER_GRAPH_PATH}. Run dataml preprocess first.")

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    num_nodes = len(config["nodes"])
    model = SpilloverGNN(
        num_nodes=num_nodes,
        in_dim=config["in_dim"],
        hidden_dim=config["hidden_dim"],
        out_dim=config["out_dim"],
    )
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    panel_df = pd.read_parquet(SAHEL_PANEL_PATH)
    graph_df = pd.read_parquet(SPILLOVER_GRAPH_PATH)
    node_to_idx = {k: int(v) for k, v in config["node_to_idx"].items()}

    return model, config, panel_df, graph_df, node_to_idx


def _get_baseline_row(panel_df: pd.DataFrame, node_iso3: str) -> Dict[str, Any]:
    """Get latest-year row for node. Raise ValueError if node not in panel."""
    subset = panel_df[panel_df["country_iso3"] == node_iso3]
    if subset.empty:
        raise ValueError(f"Node {node_iso3} not found in panel. Valid nodes: {sorted(panel_df['country_iso3'].unique().tolist())}")
    row = subset.loc[subset["year"].idxmax()]
    funding_gap = max(0.0, float(row["funding_required"]) - float(row["funding_received"]))
    return {
        "coverage": float(row["coverage"]),
        "people_in_need": int(row["people_in_need"]),
        "funding_gap_usd": funding_gap,
    }


def _run_forward(
    model: SpilloverGNN,
    panel_df: pd.DataFrame,
    graph_df: pd.DataFrame,
    node_to_idx: Dict[str, int],
    node_iso3: str,
    delta_funding_pct: float,
    horizon_years: int,
) -> Dict[str, Any]:
    """Run model forward for horizon years; return baseline, scenario, spillover_impacts, trajectory."""
    nodes = sorted(node_to_idx.keys())
    n = len(nodes)
    idx = node_to_idx.get(node_iso3)
    if idx is None:
        raise ValueError(f"Node {node_iso3} not in model. Valid: {nodes}")

    # Latest panel row per node
    latest = panel_df.loc[panel_df.groupby("country_iso3")["year"].idxmax()].set_index("country_iso3")

    cov = latest["coverage"].reindex(nodes).fillna(0.5).values.astype("float32")
    need = latest["people_in_need"].reindex(nodes).fillna(1e6).values
    gap = (latest["funding_required"] - latest["funding_received"]).reindex(nodes).fillna(0).values
    conflict = latest["conflict"].reindex(nodes).fillna(0.2).values.astype("float32")
    drought = latest["drought"].reindex(nodes).fillna(0.1).values.astype("float32")

    need_max = max(1.0, need.max())
    need_norm = (need / need_max).astype("float32")
    gap_norm = (gap / (gap.max() + 1e-6)).astype("float32")

    x = torch.tensor(
        np.column_stack([cov, need_norm, gap_norm, conflict, drought]),
        dtype=torch.float32,
    )
    src_idx, tgt_idx = get_edge_index(graph_df, node_to_idx)
    edge_index = torch.tensor([src_idx, tgt_idx], dtype=torch.long)

    delta_pct = delta_funding_pct / 100.0
    delta_funding = torch.zeros(n, dtype=torch.float32)
    delta_funding[idx] = delta_pct

    baseline_coverage = float(cov[idx])
    baseline_need = int(need[idx])
    baseline_gap = max(0.0, float(gap[idx]))

    trajectory: List[Dict[str, Any]] = []
    trajectory.append({
        "year_offset": 0,
        "coverage": round(baseline_coverage, 2),
        "people_in_need": baseline_need,
    })

    cov_cur = cov.copy()
    need_cur = need.copy()
    for t in range(1, horizon_years + 1):
        delta_funding_t = torch.zeros(n, dtype=torch.float32)
        delta_funding_t[idx] = delta_pct * (1.0 - 0.2 * (t - 1))  # decay shock over time
        need_norm_cur = (need_cur / need_max).astype("float32")
        gap_cur = (latest["funding_required"] - latest["funding_received"]).reindex(nodes).fillna(0).values
        gap_norm_cur = (gap_cur / (gap_cur.max() + 1e-6)).astype("float32")
        x_cur = torch.tensor(
            np.column_stack([cov_cur, need_norm_cur, gap_norm_cur, conflict, drought]),
            dtype=torch.float32,
        )
        with torch.no_grad():
            out = model(x_cur, edge_index, delta_funding_t)
        cov_cur = out[:, 0].numpy()
        cov_cur = np.clip(cov_cur, 0.0, 1.0)
        need_norm_next = out[:, 1].numpy()
        need_cur = (need_norm_next * need_max).astype("int64")
        need_cur = np.maximum(need_cur, 0)
        trajectory.append({
            "year_offset": t,
            "coverage": round(float(cov_cur[idx]), 2),
            "people_in_need": int(need_cur[idx]),
        })

    scenario_coverage = float(cov_cur[idx])
    scenario_need = int(need_cur[idx])
    scenario_gap = baseline_gap * (1 - delta_pct) * (1 + 0.1 * horizon_years)
    scenario_gap = max(0.0, scenario_gap)

    # Spillover impacts: neighbors' delta coverage and delta need
    spillover_impacts: List[Dict[str, Any]] = []
    neighbors = set()
    for _, r in graph_df.iterrows():
        if r["source_iso3"] == node_iso3:
            neighbors.add(r["target_iso3"])
        elif r["target_iso3"] == node_iso3:
            neighbors.add(r["source_iso3"])
    baseline_by_node = {}
    for node in nodes:
        row = latest.loc[node]
        baseline_by_node[node] = {
            "coverage": float(row["coverage"]),
            "need": int(row["people_in_need"]),
        }
    for nb in sorted(neighbors):
        if nb not in node_to_idx:
            continue
        j = node_to_idx[nb]
        dc = (float(cov_cur[j]) - baseline_by_node[nb]["coverage"]) * 100
        dn = ((int(need_cur[j]) - baseline_by_node[nb]["need"]) / max(1, baseline_by_node[nb]["need"])) * 100
        spillover_impacts.append({
            "node_iso3": nb,
            "delta_coverage_pct": round(dc, 1),
            "delta_need_pct": round(dn, 1),
        })

    return {
        "baseline": {
            "coverage": round(baseline_coverage, 2),
            "people_in_need": baseline_need,
            "funding_gap_usd": round(baseline_gap, 0),
        },
        "scenario": {
            "coverage": round(scenario_coverage, 2),
            "people_in_need": scenario_need,
            "funding_gap_usd": round(scenario_gap, 0),
        },
        "spillover_impacts": spillover_impacts,
        "trajectory": trajectory,
    }


def simulate_aftershock(
    node_iso3: str,
    delta_funding_pct: float,
    horizon_years: int,
) -> Dict[str, Any]:
    """
    Simulate funding shock at a node and return baseline, scenario, spillover, trajectory.

    Args:
        node_iso3: ISO3 country code (e.g. "MLI", "NER")
        delta_funding_pct: Funding change in percent (e.g. -10.0 for -10%)
        horizon_years: Number of years to project (1, 2, 3, etc.)

    Returns:
        Dict with: node_iso3, delta_funding_pct, horizon_years, baseline, scenario,
        spillover_impacts, trajectory.

    Raises:
        ValueError: If node_iso3 not in panel or horizon_years out of range.
        FileNotFoundError: If model/panel/graph not found (run preprocess + train first).
    """
    horizon_years = int(horizon_years)
    if horizon_years < 1 or horizon_years > 10:
        raise ValueError("horizon_years must be between 1 and 10")

    node_iso3 = node_iso3.strip().upper()

    model, config, panel_df, graph_df, node_to_idx = _load_model_and_data()

    _get_baseline_row(panel_df, node_iso3)  # validates node exists
    result = _run_forward(
        model, panel_df, graph_df, node_to_idx,
        node_iso3, delta_funding_pct, horizon_years,
    )

    return {
        "node_iso3": node_iso3,
        "delta_funding_pct": delta_funding_pct,
        "horizon_years": horizon_years,
        "baseline": result["baseline"],
        "scenario": result["scenario"],
        "spillover_impacts": result["spillover_impacts"],
        "trajectory": result["trajectory"],
    }
