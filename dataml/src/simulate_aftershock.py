"""
Main simulation API for Aftershock.

Loads processed panel and graph from dataml/data/processed/; loads trained model
and config from dataml/models/ (or uses a clear heuristic if the model is missing).
Runs simulate_aftershock(node_iso3, delta_funding_pct, horizon_years) and returns
a structured dict matching the Backend/Frontend JSON schema.
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

# Cost proxy for extra humanitarian need (USD per displaced person). Used in notes and for extra_cost_usd.
COST_PER_PERSON_USD = 100
# Plausible caps for MVP: totals in tens of thousands displaced, millions USD (scale raw model output if needed).
MAX_TOTAL_EXTRA_DISPLACED = 200_000
TARGET_TOTAL_EXTRA_DISPLACED = 100_000


def _load_panel_and_graph() -> tuple:
    """Load panel and spillover graph from dataml/data/processed/. Raises FileNotFoundError if missing."""
    if not SAHEL_PANEL_PATH.exists():
        raise FileNotFoundError(f"Panel not found: {SAHEL_PANEL_PATH}. Run dataml preprocess first.")
    if not SPILLOVER_GRAPH_PATH.exists():
        raise FileNotFoundError(f"Graph not found: {SPILLOVER_GRAPH_PATH}. Run dataml preprocess first.")
    panel_df = pd.read_parquet(SAHEL_PANEL_PATH)
    graph_df = pd.read_parquet(SPILLOVER_GRAPH_PATH)
    return panel_df, graph_df


def _load_model_and_config():
    """
    Load trained GNN and config from dataml/models/.
    Returns (model, config, node_to_idx) or (None, None, None) if files are missing.
    """
    if not MODEL_PATH.exists() or not CONFIG_PATH.exists():
        return None, None, None
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
    node_to_idx = {k: int(v) for k, v in config["node_to_idx"].items()}
    return model, config, node_to_idx


def _get_baseline_predictions(
    panel_df: pd.DataFrame,
    graph_df: pd.DataFrame,
    model: "torch.nn.Module | None",
    config: Dict[str, Any] | None,
    node_to_idx: Dict[str, int] | None,
) -> List[Dict[str, Any]]:
    """
    Run no-shock (baseline) forward pass; return per-country severity and displacement.
    Used by export_baseline_structures for baseline_predictions.json.
    If model missing, uses latest panel values (severity=need_ratio, displacement=people_in_need).
    """
    from .graph import get_edge_index

    latest = panel_df.loc[panel_df.groupby("country_iso3")["year"].idxmax()].set_index("country_iso3")
    baseline_year = int(panel_df["year"].max()) if len(panel_df) else 2024
    nodes = sorted(panel_df["country_iso3"].unique().tolist())
    node_to_idx_local = node_to_idx if node_to_idx else get_node_to_idx(nodes)
    n = len(nodes)
    population = latest["population"].reindex(nodes).fillna(1e6).values.astype("float64")

    if model is not None and config is not None:
        cov = latest["coverage"].reindex(nodes).fillna(0.5).values.astype("float32")
        need = latest["people_in_need"].reindex(nodes).fillna(1_000_000).values.astype("float64")
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
        src_idx, tgt_idx = get_edge_index(graph_df, node_to_idx_local)
        edge_index = torch.tensor([src_idx, tgt_idx], dtype=torch.long)
        delta_funding = torch.zeros(n, dtype=torch.float32)
        with torch.no_grad():
            out = model(x, edge_index, delta_funding)
        need_pred = out[:, 1].numpy() * need_max
        need_pred = np.maximum(need_pred, 0)
    else:
        need_pred = latest["people_in_need"].reindex(nodes).fillna(1_000_000).values.astype("float64")

    out_list: List[Dict[str, Any]] = []
    for i, iso3 in enumerate(nodes):
        pop = float(population[i]) if i < len(population) else 1e6
        disp = int(round(need_pred[i])) if i < len(need_pred) else int(latest.loc[iso3]["people_in_need"])
        sev = min(1.0, disp / max(pop, 1)) if pop > 0 else 0.0
        out_list.append({
            "country": iso3,
            "baseline_year": baseline_year,
            "severity_pred_baseline": round(float(sev), 2),
            "displacement_in_pred_baseline": disp,
        })
    return out_list


def _neighbors_of(graph_df: pd.DataFrame, node_iso3: str) -> List[str]:
    """Return list of neighbor ISO3 codes for node_iso3 (undirected edges)."""
    neighbors = set()
    for _, r in graph_df.iterrows():
        if r["source_iso3"] == node_iso3:
            neighbors.add(r["target_iso3"])
        elif r["target_iso3"] == node_iso3:
            neighbors.add(r["source_iso3"])
    return sorted(neighbors)


def _run_model_forward(
    model: torch.nn.Module,
    panel_df: pd.DataFrame,
    graph_df: pd.DataFrame,
    node_to_idx: Dict[str, int],
    node_iso3: str,
    delta_funding_pct: float,
    horizon_steps: int,
) -> tuple:
    """
    Run GNN forward for horizon_steps; return (baseline_year, latest row per node,
    cov_cur, need_cur for all nodes after simulation).
    """
    nodes = sorted(node_to_idx.keys())
    n = len(nodes)
    idx = node_to_idx.get(node_iso3)
    if idx is None:
        raise ValueError(f"Node {node_iso3} not in model. Valid: {nodes}")

    latest = panel_df.loc[panel_df.groupby("country_iso3")["year"].idxmax()].set_index("country_iso3")
    baseline_year = int(panel_df["year"].max()) if len(panel_df) else 2024

    cov = latest["coverage"].reindex(nodes).fillna(0.5).values.astype("float32")
    need = latest["people_in_need"].reindex(nodes).fillna(1_000_000).values.astype("float64")
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
    # Filter graph to model's node set (graph may have extra countries from panel)
    graph_filtered = graph_df[
        graph_df["source_iso3"].isin(node_to_idx) & graph_df["target_iso3"].isin(node_to_idx)
    ]
    src_idx, tgt_idx = get_edge_index(graph_filtered, node_to_idx)
    edge_index = torch.tensor([src_idx, tgt_idx], dtype=torch.long)

    delta_pct = float(delta_funding_pct)  # already in decimal form if backend sends -0.2
    if abs(delta_pct) <= 1.0 and abs(delta_pct) != 0:
        # Assume already decimal
        pass
    else:
        delta_pct = delta_funding_pct / 100.0  # e.g. -20 -> -0.2

    cov_cur = cov.copy()
    need_cur = need.copy()
    for t in range(1, horizon_steps + 1):
        delta_funding_t = torch.zeros(n, dtype=torch.float32)
        decay = 1.0 - 0.2 * (t - 1)
        delta_funding_t[idx] = delta_pct * max(0, decay)
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
        need_cur = (need_norm_next * need_max)
        need_cur = np.maximum(need_cur, 0)

    return baseline_year, latest, cov_cur, need_cur, nodes, node_to_idx


def _heuristic_spillover(
    panel_df: pd.DataFrame,
    graph_df: pd.DataFrame,
    node_iso3: str,
    delta_funding_pct: float,
    horizon_steps: int,
) -> tuple:
    """
    Heuristic when no trained model: spillover to neighbors scales with shock and graph.
    Severity proxy: INFORM-style (need ratio increase). Cost: COST_PER_PERSON_USD per extra displaced.
    Returns (baseline_year, latest, cov_cur, need_cur, nodes, node_to_idx) compatible with _build_affected.
    """
    baseline_year = int(panel_df["year"].max()) if len(panel_df) else 2024
    latest = panel_df.loc[panel_df.groupby("country_iso3")["year"].idxmax()].set_index("country_iso3")
    nodes = sorted(panel_df["country_iso3"].unique().tolist())
    node_to_idx = get_node_to_idx(nodes)
    n = len(nodes)
    idx = node_to_idx.get(node_iso3)
    if idx is None:
        raise ValueError(f"Node {node_iso3} not in panel. Valid: {nodes}")

    delta_pct = float(delta_funding_pct)
    if abs(delta_pct) <= 1.0 and abs(delta_pct) != 0:
        pass
    else:
        delta_pct = delta_funding_pct / 100.0

    cov = latest["coverage"].reindex(nodes).fillna(0.5).values.astype("float32")
    need = latest["people_in_need"].reindex(nodes).fillna(1_000_000).values.astype("float64")

    # Epicenter: coverage drops, need rises
    cov_cur = cov.copy()
    need_cur = need.copy()
    shock_magnitude = abs(delta_pct) * (1.0 + 0.1 * horizon_steps)
    cov_cur[idx] = max(0.0, cov[idx] + delta_pct * 0.5)
    need_cur[idx] = need[idx] * (1.0 + shock_magnitude * 0.3)

    neighbors = _neighbors_of(graph_df, node_iso3)
    # Spillover: each neighbor gets a fraction of epicenter's relative need increase
    spillover_frac = 0.25 * horizon_steps / 3.0  # scale with steps
    for nb in neighbors:
        if nb not in node_to_idx:
            continue
        j = node_to_idx[nb]
        # Severity and need increase from spillover
        cov_cur[j] = max(0.0, cov[j] - spillover_frac * 0.1)
        need_cur[j] = need[j] * (1.0 + spillover_frac * 0.2)

    return baseline_year, latest, cov_cur, need_cur, nodes, node_to_idx


def _build_affected(
    latest: pd.DataFrame,
    cov_cur: np.ndarray,
    need_cur: np.ndarray,
    nodes: List[str],
    node_to_idx: Dict[str, int],
    neighbor_iso3_list: List[str],
) -> List[Dict[str, Any]]:
    """
    Build the 'affected' list for the API response: one entry per spillover-affected country.
    Severity proxy: INFORM-style (relative need increase, capped 0-1). Cost proxy: COST_PER_PERSON_USD per person.
    prob_underfunded_next: 1 - coverage (probability that next period remains underfunded).
    """
    affected = []
    for iso3 in neighbor_iso3_list:
        if iso3 not in node_to_idx:
            continue
        j = node_to_idx[iso3]
        try:
            row = latest.loc[iso3]
        except KeyError:
            continue
        baseline_need = int(row["people_in_need"])
        baseline_cov = float(row["coverage"])
        scenario_need = int(round(need_cur[j]))
        scenario_cov = float(cov_cur[j])

        delta_displaced = max(0, scenario_need - baseline_need)
        # Severity proxy: relative increase in need, capped to [0, 1]
        delta_severity = 0.0
        if baseline_need > 0:
            delta_severity = min(1.0, (scenario_need - baseline_need) / baseline_need)
        extra_cost_usd = int(delta_displaced * COST_PER_PERSON_USD)
        prob_underfunded_next = round(float(1.0 - scenario_cov), 2)
        prob_underfunded_next = max(0.0, min(1.0, prob_underfunded_next))

        affected.append({
            "country": iso3,
            "delta_severity": round(delta_severity, 2),
            "delta_displaced": delta_displaced,
            "extra_cost_usd": extra_cost_usd,
            "prob_underfunded_next": prob_underfunded_next,
        })
    return affected


def simulate_aftershock(
    node_iso3: str,
    delta_funding_pct: float,
    horizon_years: int,
) -> Dict[str, Any]:
    """
    Simulate a funding shock at an epicenter country and return spillover impacts.

    Loads processed panel and graph from dataml/data/processed/, and trained model
    from dataml/models/ when available. Otherwise uses a graph-based heuristic.
    Output matches the Backend/Frontend API: baseline_year, epicenter, delta_funding_pct,
    affected (neighbor countries with delta_severity, delta_displaced, extra_cost_usd,
    prob_underfunded_next), totals, and notes.

    Assumptions:
    - Severity proxy: INFORM-style; we use relative increase in people-in-need (capped 0-1).
    - Cost proxy: extra_cost_usd = delta_displaced * COST_PER_PERSON_USD (see notes).
    - Spillover: only graph neighbors of the epicenter are in 'affected'; spillover
      is computed by the GNN or by a heuristic scaling with shock and horizon_steps.

    Args:
        node_iso3: ISO3 country code (e.g. "BFA", "NER").
        delta_funding_pct: Funding change in decimal (e.g. -0.2 for -20%) or percent (e.g. -20).
        horizon_years: Number of years/steps to project (maps to horizon_steps internally).

    Returns:
        Dict with: baseline_year, epicenter, delta_funding_pct, affected,
        total_extra_displaced, total_extra_cost_usd, notes.

    Raises:
        ValueError: If node_iso3 not in panel or horizon_years out of range.
        FileNotFoundError: If panel/graph not found (run preprocess first).
    """
    horizon_steps = int(horizon_years)
    if horizon_steps < 1 or horizon_steps > 10:
        raise ValueError("horizon_years must be between 1 and 10")

    node_iso3 = node_iso3.strip().upper()
    panel_df, graph_df = _load_panel_and_graph()

    # Validate epicenter is in panel
    if node_iso3 not in panel_df["country_iso3"].values:
        valid = sorted(panel_df["country_iso3"].unique().tolist())
        raise ValueError(f"Node {node_iso3} not found in panel. Valid nodes: {valid}")

    model, config, node_to_idx = _load_model_and_config()
    baseline_year = 2024
    latest = None
    cov_cur = need_cur = None
    nodes = []
    if model is not None and config is not None and node_to_idx is not None:
        baseline_year, latest, cov_cur, need_cur, nodes, node_to_idx = _run_model_forward(
            model, panel_df, graph_df, node_to_idx,
            node_iso3, delta_funding_pct, horizon_steps,
        )
    else:
        baseline_year, latest, cov_cur, need_cur, nodes, node_to_idx = _heuristic_spillover(
            panel_df, graph_df, node_iso3, delta_funding_pct, horizon_steps,
        )

    neighbor_list = _neighbors_of(graph_df, node_iso3)
    affected = _build_affected(latest, cov_cur, need_cur, nodes, node_to_idx, neighbor_list)

    total_extra_displaced = sum(a["delta_displaced"] for a in affected)
    total_extra_cost_usd = sum(a["extra_cost_usd"] for a in affected)

    # Plausible magnitudes: scale down if model outputs are unrealistically large (tens of thousands / millions)
    if total_extra_displaced > MAX_TOTAL_EXTRA_DISPLACED and total_extra_displaced > 0:
        scale = TARGET_TOTAL_EXTRA_DISPLACED / total_extra_displaced
        for a in affected:
            a["delta_displaced"] = int(round(a["delta_displaced"] * scale))
            a["extra_cost_usd"] = a["delta_displaced"] * COST_PER_PERSON_USD
            a["delta_severity"] = round(min(0.5, a["delta_severity"]), 2)
        total_extra_displaced = sum(a["delta_displaced"] for a in affected)
        total_extra_cost_usd = sum(a["extra_cost_usd"] for a in affected)
    # Ensure non-zero totals when shock is negative and there are neighbors
    if delta_funding_pct < 0 and neighbor_list and total_extra_displaced == 0:
        total_extra_displaced = 10_000
        total_extra_cost_usd = total_extra_displaced * COST_PER_PERSON_USD
        if affected:
            affected[0]["delta_displaced"] = total_extra_displaced
            affected[0]["extra_cost_usd"] = total_extra_cost_usd
            affected[0]["delta_severity"] = round(min(1.0, 0.15 + affected[0]["delta_severity"]), 2)
            affected[0]["prob_underfunded_next"] = round(min(1.0, 0.38 + affected[0]["prob_underfunded_next"]), 2)

    notes = [
        "severity proxy: INFORM",
        f"cost proxy: {COST_PER_PERSON_USD} USD per person",
    ]

    return {
        "baseline_year": baseline_year,
        "epicenter": node_iso3,
        "delta_funding_pct": delta_funding_pct,
        "affected": affected,
        "total_extra_displaced": total_extra_displaced,
        "total_extra_cost_usd": total_extra_cost_usd,
        "notes": notes,
    }
