"""
Train PyTorch spillover model for Aftershock.

Loads processed panel and graph, trains a GNN that predicts downstream humanitarian
outcomes given node-level shocks and graph structure.
Saves dataml/models/spillover_model.pt and model_config.json.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from .graph import get_edge_index, get_node_to_idx

log = logging.getLogger(__name__)

# Paths relative to dataml/ (parent of src/)
DATAML_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"
MODELS_DIR = DATAML_ROOT / "models"

SAHEL_PANEL_PATH = PROCESSED_DIR / "sahel_panel.parquet"
SPILLOVER_GRAPH_PATH = PROCESSED_DIR / "spillover_graph.parquet"
FEATURES_PATH = PROCESSED_DIR / "features.parquet"
MODEL_PATH = MODELS_DIR / "spillover_model.pt"
CONFIG_PATH = MODELS_DIR / "model_config.json"

HIDDEN_DIM = 32
NUM_LAYERS = 2
EPOCHS = 100
LR = 1e-3
HORIZON_MAX = 5


class SpilloverGNN(nn.Module):
    """
    Simple 2-layer GNN for spillover prediction.

    Message passing: aggregate neighbor features, then MLP per node.
    Input: node features (coverage, people_in_need_norm, funding_gap_norm, conflict, drought)
    Output: predicted coverage, people_in_need for next step.
    """

    def __init__(self, num_nodes: int, in_dim: int, hidden_dim: int, out_dim: int = 2):
        super().__init__()
        self.num_nodes = num_nodes
        self.in_dim = in_dim
        self.hidden_dim = hidden_dim
        self.out_dim = out_dim  # coverage, people_in_need (normalized)

        self.fc1 = nn.Linear(in_dim * 2 + 1, hidden_dim)  # *2 for self + neighbor agg, +1 delta_funding
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, out_dim)
        self.act = nn.ReLU()

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        delta_funding: torch.Tensor,
    ) -> torch.Tensor:
        """
        x: [num_nodes, in_dim]
        edge_index: [2, num_edges] (source, target)
        delta_funding: [num_nodes] (funding shock at each node)
        Returns: [num_nodes, out_dim] (coverage, people_in_need_norm)
        """
        src, tgt = edge_index[0], edge_index[1]
        # Aggregate neighbor features
        agg = torch.zeros(x.size(0), x.size(1), device=x.device, dtype=x.dtype)
        agg.index_add_(0, tgt, x[src])
        degree = torch.zeros(x.size(0), device=x.device, dtype=x.dtype)
        degree.index_add_(0, tgt, torch.ones_like(x[src, 0]))
        degree = degree.clamp(min=1)
        agg = agg / degree.unsqueeze(1)

        # Concat self + neighbor, plus delta_funding
        delta = delta_funding.unsqueeze(1).to(x.dtype)
        h = torch.cat([x, agg, delta], dim=1)

        h = self.act(self.fc1(h))
        h = self.act(self.fc2(h))
        out = self.fc_out(h)
        return out


def _build_training_data(
    panel_df: pd.DataFrame,
    graph_df: pd.DataFrame,
    node_to_idx: Dict[str, int],
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Build synthetic training pairs: (x, edge_index, delta_funding) -> (coverage, people_in_need)."""
    nodes = sorted(node_to_idx.keys())
    n = len(nodes)

    # Latest year per node as baseline
    latest = panel_df.loc[panel_df.groupby("country_iso3")["year"].idxmax()]
    latest = latest.set_index("country_iso3")

    # Feature matrix
    cov = latest["coverage"].reindex(nodes).fillna(0.5).values
    need = latest["people_in_need"].reindex(nodes).fillna(1e6).values
    gap = (latest["funding_required"] - latest["funding_received"]).reindex(nodes).fillna(0).values
    conflict = latest["conflict"].reindex(nodes).fillna(0.2).values
    drought = latest["drought"].reindex(nodes).fillna(0.1).values

    need_norm = np.log1p(need) / (np.log1p(need).max() + 1e-6)
    gap_norm = np.log1p(np.maximum(gap, 0)) / (np.log1p(gap.max() + 1) + 1e-6)

    x = np.stack([cov, need_norm, gap_norm, conflict, drought], axis=1).astype(np.float32)
    x = torch.tensor(x)

    src_idx, tgt_idx = get_edge_index(graph_df, node_to_idx)
    edge_index = torch.tensor([src_idx, tgt_idx], dtype=torch.long)

    # Synthetic shocks: random delta_funding at random nodes
    rng = np.random.default_rng(42)
    delta_funding = np.zeros(n, dtype=np.float32)
    shock_nodes = rng.choice(n, size=min(3, n), replace=False)
    delta_funding[shock_nodes] = rng.uniform(-0.2, 0.1, size=len(shock_nodes))

    # Target: perturbed coverage/need (simplified)
    cov_next = np.clip(cov + delta_funding * 0.5 + rng.normal(0, 0.02, n), 0, 1)
    need_next = np.log1p(need * (1 - delta_funding * 0.3) + rng.uniform(0, 1e5, n))
    need_next = need_next / (need_next.max() + 1e-6)
    y = np.stack([cov_next, need_next], axis=1).astype(np.float32)
    y = torch.tensor(y)

    return x, edge_index, torch.tensor(delta_funding), y


def train_model(
    panel_path: Path = SAHEL_PANEL_PATH,
    graph_path: Path = SPILLOVER_GRAPH_PATH,
    model_path: Path = MODEL_PATH,
    config_path: Path = CONFIG_PATH,
) -> None:
    """Train spillover model and save checkpoint + config."""
    panel_df = pd.read_parquet(panel_path)
    graph_df = pd.read_parquet(graph_path)

    nodes = sorted(panel_df["country_iso3"].unique().tolist())
    node_to_idx = get_node_to_idx(nodes)
    num_nodes = len(nodes)
    in_dim = 5  # coverage, need_norm, gap_norm, conflict, drought
    hidden_dim = HIDDEN_DIM
    out_dim = 2

    x, edge_index, delta_funding, y = _build_training_data(panel_df, graph_df, node_to_idx)

    model = SpilloverGNN(num_nodes=num_nodes, in_dim=in_dim, hidden_dim=hidden_dim, out_dim=out_dim)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.MSELoss()

    for ep in range(EPOCHS):
        model.train()
        opt.zero_grad()
        pred = model(x, edge_index, delta_funding)
        loss = loss_fn(pred, y)
        loss.backward()
        opt.step()
        if (ep + 1) % 20 == 0:
            log.info(f"Epoch {ep+1}/{EPOCHS} loss={loss.item():.4f}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "num_nodes": num_nodes,
            "in_dim": in_dim,
            "hidden_dim": hidden_dim,
            "out_dim": out_dim,
        },
        model_path,
    )

    config: Dict[str, Any] = {
        "nodes": nodes,
        "node_to_idx": node_to_idx,
        "in_dim": in_dim,
        "hidden_dim": hidden_dim,
        "out_dim": out_dim,
        "horizon_max": HORIZON_MAX,
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    log.info(f"Model saved to {model_path}")
    log.info(f"Config saved to {config_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_model()
