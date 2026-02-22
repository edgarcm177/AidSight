"""
Crisis and project embeddings for Actian VectorAI.

Builds fixed-length numeric embeddings from sahel_panel and project_metrics,
suitable for vector similarity search. Uses standardized numeric features only
(no SentenceTransformers or TF-IDF to avoid extra dependencies). Text descriptions
are also generated for each row for display and optional text-based retrieval.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

DATAML_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"

SAHEL_PANEL_PATH = PROCESSED_DIR / "sahel_panel.parquet"
PROJECT_METRICS_PATH = PROCESSED_DIR / "project_metrics.parquet"
CRISIS_EMBEDDINGS_PATH = PROCESSED_DIR / "crisis_embeddings.parquet"
PROJECT_EMBEDDINGS_PATH = PROCESSED_DIR / "project_embeddings.parquet"

CLUSTERS = ["Health", "WASH", "Food", "Shelter", "Protection", "Education", "NFI"]


def _standardize(X: np.ndarray) -> np.ndarray:
    """Standardize features: (X - mean) / std."""
    mean_ = X.mean(axis=0)
    std_ = X.std(axis=0)
    std_[std_ < 1e-9] = 1.0
    return (X - mean_) / std_


def build_crisis_embeddings(panel_path: Path = SAHEL_PANEL_PATH) -> pd.DataFrame:
    """
    Build crisis embeddings from sahel_panel.parquet.

    For each (country_iso3, year): builds a text description and a numeric feature
    vector (severity, underfunding_score, coverage, log funding_total_usd,
    chronic_underfunded_flag). Standardizes and stores as fixed-length embedding.
    Saves crisis_embeddings.parquet.
    """
    if not panel_path.exists():
        raise FileNotFoundError(f"Panel not found: {panel_path}. Run preprocess first.")

    panel = pd.read_parquet(panel_path)

    # Description
    panel["description"] = panel.apply(
        lambda r: (
            f"Crisis in {r['country_iso3']} in {r['year']}: "
            f"severity={r.get('severity', 0):.2f}, funding={r.get('funding_total_usd', 0):.0f}, "
            f"underfunding_score={r.get('underfunding_score', 0):.2f}, "
            f"chronic={r.get('chronic_underfunded_flag', 0)}."
        ),
        axis=1,
    )

    # Numeric features for embedding
    severity = panel["severity"].fillna(0.2).values.astype(np.float64)
    underfunding = panel["underfunding_score"].fillna(0.5).values.astype(np.float64)
    coverage = panel["coverage"].fillna(0.5).values.astype(np.float64)
    funding = panel["funding_total_usd"].fillna(0).clip(lower=1).values.astype(np.float64)
    chronic = panel["chronic_underfunded_flag"].fillna(0).values.astype(np.float64)

    X = np.column_stack([
        severity,
        underfunding,
        coverage,
        np.log1p(funding),
        chronic,
    ])
    X_std = _standardize(X)

    panel["embedding"] = [X_std[i].tolist() for i in range(len(panel))]

    out = panel[["country_iso3", "year", "severity", "underfunding_score", "chronic_underfunded_flag", "description", "embedding"]].copy()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CRISIS_EMBEDDINGS_PATH, index=False)
    log.info(f"Crisis embeddings: {len(out)} rows -> {CRISIS_EMBEDDINGS_PATH}")
    return out


def build_project_embeddings(
    project_metrics_path: Path = PROJECT_METRICS_PATH,
    panel_path: Path = SAHEL_PANEL_PATH,
) -> pd.DataFrame:
    """
    Build project embeddings from project_metrics.parquet.

    Joins with latest year crisis panel for severity and underfunding_score.
    For each project: builds text description and numeric feature vector
    (ratio_reached, underfunding_score, log budget, log beneficiaries, cluster ordinal).
    Standardizes and stores as fixed-length embedding. Saves project_embeddings.parquet.
    """
    if not project_metrics_path.exists():
        raise FileNotFoundError(f"Project metrics not found: {project_metrics_path}. Run export_project_benchmarking first.")
    if not panel_path.exists():
        raise FileNotFoundError(f"Panel not found: {panel_path}. Run preprocess first.")

    pm = pd.read_parquet(project_metrics_path)
    panel = pd.read_parquet(panel_path)
    latest = panel.loc[panel.groupby("country_iso3")["year"].idxmax()].set_index("country_iso3")

    pm = pm.merge(
        latest[["severity", "underfunding_score"]].add_prefix("crisis_"),
        left_on="country_iso3",
        right_index=True,
        how="left",
    )
    pm["underfunding_score"] = pm["crisis_underfunding_score"].fillna(0.5)
    pm = pm.drop(columns=["crisis_severity", "crisis_underfunding_score"], errors="ignore")

    # Description
    pm["description"] = pm.apply(
        lambda r: (
            f"Project {r['project_id']} in {r['country_iso3']}, {r['year']}, "
            f"cluster={r['cluster']}, budget={r['budget_usd']:.0f}, "
            f"beneficiaries={r['beneficiaries']}, ratio={r['ratio_reached']:.4f}, "
            f"outlier={r['outlier_flag']}."
        ),
        axis=1,
    )

    # Numeric features
    cluster_ord = {c: i for i, c in enumerate(CLUSTERS)}
    pm["cluster_ord"] = pm["cluster"].map(lambda x: cluster_ord.get(x, 0))

    X = np.column_stack([
        pm["ratio_reached"].values.astype(np.float64),
        pm["underfunding_score"].values.astype(np.float64),
        np.log1p(pm["budget_usd"].values).astype(np.float64),
        np.log1p(pm["beneficiaries"].values).astype(np.float64),
        pm["cluster_ord"].values.astype(np.float64),
    ])
    X_std = _standardize(X)

    pm["embedding"] = [X_std[i].tolist() for i in range(len(pm))]

    out = pm[["project_id", "country_iso3", "year", "cluster", "ratio_reached", "outlier_flag", "description", "embedding"]].copy()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROJECT_EMBEDDINGS_PATH, index=False)
    log.info(f"Project embeddings: {len(out)} rows -> {PROJECT_EMBEDDINGS_PATH}")
    return out
