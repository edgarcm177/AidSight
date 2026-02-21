"""
Spillover graph construction for Aftershock.

Defines spillover edges (adjacency, weights) between Sahel-region countries.
Edges represent shared borders, displacement flows, or conflict diffusion.
Exports graph in format usable by PyTorch (edge index, optional weights).
"""

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

# Sahel and neighboring nodes: MLI, NER, BFA, TCD, CMR, NGA, SEN, MRT, GMB, SDN, SSD, CAF
SAHEL_ISO3 = frozenset(
    {"MLI", "NER", "BFA", "TCD", "CMR", "NGA", "SEN", "MRT", "GMB", "SDN", "SSD", "CAF"}
)

# Adjacency by shared borders / regional spillover (undirected)
# Based on geographic neighbors in Sahel/Sahel-adjacent region
SPILLOVER_EDGES: List[Tuple[str, str]] = [
    ("MLI", "NER"),
    ("MLI", "BFA"),
    ("MLI", "MRT"),
    ("MLI", "SEN"),
    ("NER", "BFA"),
    ("NER", "TCD"),
    ("NER", "NGA"),
    ("NER", "MRT"),
    ("BFA", "TCD"),
    ("BFA", "GMB"),
    ("BFA", "MRT"),
    ("BFA", "SEN"),
    ("TCD", "CMR"),
    ("TCD", "NGA"),
    ("TCD", "SDN"),
    ("TCD", "CAF"),
    ("CMR", "NGA"),
    ("CMR", "CAF"),
    ("NGA", "CMR"),
    ("SEN", "GMB"),
    ("SEN", "MRT"),
    ("SDN", "SSD"),
    ("SSD", "CAF"),
]


def build_spillover_graph(panel_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build spillover graph from panel nodes and predefined edges.

    Uses SPILLOVER_EDGES filtered by nodes present in panel.
    Returns DataFrame with columns: source_iso3, target_iso3, weight.
    """
    nodes_in_panel = set(panel_df["country_iso3"].unique())
    edges = []
    for src, tgt in SPILLOVER_EDGES:
        if src in nodes_in_panel and tgt in nodes_in_panel:
            edges.append({"source_iso3": src, "target_iso3": tgt, "weight": 1.0})
    return pd.DataFrame(edges)


def get_edge_index(
    graph_df: pd.DataFrame, node_to_idx: Dict[str, int]
) -> Tuple[List[int], List[int]]:
    """
    Convert graph DataFrame to PyTorch-style edge index (COO format).

    Returns (source_indices, target_indices) as lists.
    """
    src_idx = [node_to_idx[r["source_iso3"]] for _, r in graph_df.iterrows()]
    tgt_idx = [node_to_idx[r["target_iso3"]] for _, r in graph_df.iterrows()]
    return src_idx, tgt_idx


def get_node_to_idx(nodes: List[str]) -> Dict[str, int]:
    """Map ISO3 to integer index (consistent ordering)."""
    sorted_nodes = sorted(nodes)
    return {n: i for i, n in enumerate(sorted_nodes)}


def load_graph(path: Path) -> pd.DataFrame:
    """Load spillover graph from parquet."""
    return pd.read_parquet(path)


def save_graph(graph_df: pd.DataFrame, path: Path) -> None:
    """Save spillover graph to parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    graph_df.to_parquet(path, index=False)
