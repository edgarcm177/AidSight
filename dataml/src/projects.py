"""
Project-level outliers and doppelgänger benchmarking for Aftershock.

Builds a synthetic projects table (when no real project data exists), computes
ratio_reached and outlier flags per (cluster, country_iso3), and finds k-nearest
neighbor projects by feature similarity. Saves project_metrics.parquet and
project_neighbors.parquet for export.
"""

import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

DATAML_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"

PROJECTS_PATH = PROCESSED_DIR / "projects.parquet"
PROJECT_METRICS_PATH = PROCESSED_DIR / "project_metrics.parquet"
PROJECT_NEIGHBORS_PATH = PROCESSED_DIR / "project_neighbors.parquet"
SAHEL_PANEL_PATH = PROCESSED_DIR / "sahel_panel.parquet"

# Clusters for synthetic projects (standard humanitarian clusters)
CLUSTERS = ["Health", "WASH", "Food", "Shelter", "Protection", "Education", "NFI"]

K_NEIGHBORS = 3


def build_synthetic_projects(panel_path: Path = SAHEL_PANEL_PATH) -> pd.DataFrame:
    """
    Build a synthetic projects table when no real project data exists.
    Uses Sahel panel to anchor country-year combinations; assigns clusters,
    budgets (millions), and beneficiaries (tens/hundreds of thousands).
    For benchmarking logic only; clearly synthetic.
    """
    if not panel_path.exists():
        raise FileNotFoundError(f"Panel not found: {panel_path}. Run preprocess first.")

    panel = pd.read_parquet(panel_path)
    rng = np.random.default_rng(42)

    rows = []
    project_id = 0
    for _, row in panel.iterrows():
        country = row["country_iso3"]
        year = int(row["year"])
        pin = int(row["people_in_need"])
        sev = float(row["severity"]) if "severity" in panel.columns else 0.2
        # 2-5 projects per country-year
        n_proj = rng.integers(2, 6)
        for _ in range(n_proj):
            cluster = rng.choice(CLUSTERS)
            # Budget: 1-50M USD, slightly higher for higher severity
            budget_usd = float(rng.integers(1_000_000, 50_000_001))
            budget_usd *= 1.0 + 0.5 * sev
            # Beneficiaries: 10k-500k, tied to country need
            ben = int(rng.integers(10_000, min(500_001, pin + 100_000)))
            ben = min(ben, pin * 2)
            rows.append({
                "project_id": f"P{project_id:05d}",
                "country_iso3": country,
                "year": year,
                "cluster": cluster,
                "budget_usd": round(budget_usd, 0),
                "beneficiaries": ben,
            })
            project_id += 1

    df = pd.DataFrame(rows)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROJECTS_PATH, index=False)
    log.info(f"Built synthetic projects: {len(df)} rows -> {PROJECTS_PATH}")
    return df


def compute_project_metrics(projects_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Compute ratio_reached = beneficiaries / max(budget_usd, 1) and outlier_flag
    per (cluster, country_iso3). Outlier: high if > median + 1.5*IQR, low if
    < median - 1.5*IQR, else normal.
    Saves project_metrics.parquet.
    """
    if projects_df is None:
        if PROJECTS_PATH.exists():
            projects_df = pd.read_parquet(PROJECTS_PATH)
        else:
            projects_df = build_synthetic_projects()

    df = projects_df.copy()
    df["ratio_reached"] = df["beneficiaries"] / df["budget_usd"].clip(lower=1)

    def flag_outlier(g: pd.DataFrame) -> pd.Series:
        r = g["ratio_reached"]
        med = r.median()
        q1, q3 = r.quantile(0.25), r.quantile(0.75)
        iqr = max(q3 - q1, 1e-9)
        low = med - 1.5 * iqr
        high = med + 1.5 * iqr
        flags = np.where(r > high, "high", np.where(r < low, "low", "normal"))
        return pd.Series(flags, index=g.index)

    df["outlier_flag"] = df.groupby(["cluster", "country_iso3"], group_keys=False).apply(flag_outlier, include_groups=False)

    out = df[["project_id", "country_iso3", "year", "cluster", "budget_usd", "beneficiaries", "ratio_reached", "outlier_flag"]].copy()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROJECT_METRICS_PATH, index=False)
    log.info(f"Project metrics: {len(out)} rows -> {PROJECT_METRICS_PATH}")
    return out


def compute_project_neighbors(
    project_metrics_df: Optional[pd.DataFrame] = None,
    panel_path: Path = SAHEL_PANEL_PATH,
    k: int = K_NEIGHBORS,
) -> pd.DataFrame:
    """
    Join project_metrics with panel; build feature vector (cluster ordinal,
    underfunding_score, severity, log budget, log beneficiaries). Standardize,
    find k nearest neighbors by Euclidean distance. Returns project_neighbors
    with project_id, neighbor_id, similarity_score, neighbor_ratio_reached.
    similarity_score = 1 - normalized_dist so higher = more similar.
    """
    if project_metrics_df is None:
        if PROJECT_METRICS_PATH.exists():
            project_metrics_df = pd.read_parquet(PROJECT_METRICS_PATH)
        else:
            project_metrics_df = compute_project_metrics()

    if not panel_path.exists():
        raise FileNotFoundError(f"Panel not found: {panel_path}. Run preprocess first.")

    panel = pd.read_parquet(panel_path)
    latest = panel.loc[panel.groupby("country_iso3")["year"].idxmax()].set_index("country_iso3")

    pm = project_metrics_df.copy()
    panel_cols = [c for c in ["severity", "underfunding_score"] if c in latest.columns]
    if panel_cols:
        join_df = latest[panel_cols].add_suffix("_pnl")
        pm = pm.merge(join_df, left_on="country_iso3", right_index=True, how="left")
        pm["severity"] = pm["severity_pnl"].fillna(0.2) if "severity_pnl" in pm.columns else 0.2
        pm["underfunding_score"] = pm["underfunding_score_pnl"].fillna(0.5) if "underfunding_score_pnl" in pm.columns else 0.5
        pm = pm.drop(columns=[c for c in pm.columns if c.endswith("_pnl")], errors="ignore")
    else:
        pm["severity"] = 0.2
        pm["underfunding_score"] = 0.5

    cluster_ord = {c: i for i, c in enumerate(CLUSTERS)}
    pm["cluster_ord"] = pm["cluster"].map(lambda x: cluster_ord.get(x, 0))

    X = np.column_stack([
        pm["cluster_ord"].values.astype(np.float64),
        pm["underfunding_score"].values.astype(np.float64),
        pm["severity"].values.astype(np.float64),
        np.log1p(pm["budget_usd"].values).astype(np.float64),
        np.log1p(pm["beneficiaries"].values).astype(np.float64),
    ])

    mean_ = X.mean(axis=0)
    std_ = X.std(axis=0)
    std_[std_ < 1e-9] = 1.0
    X_std = (X - mean_) / std_

    n = len(pm)
    ratio = pm["ratio_reached"].values
    ids = pm["project_id"].values

    rows = []
    for i in range(n):
        dists = np.linalg.norm(X_std - X_std[i], axis=1)
        dists[i] = np.inf
        idx = np.argsort(dists)[:k]
        for j in idx:
            d = dists[j]
            sim = 1.0 / (1.0 + d)  # higher = more similar
            rows.append({
                "project_id": ids[i],
                "neighbor_id": ids[j],
                "similarity_score": round(float(sim), 4),
                "neighbor_ratio_reached": round(float(ratio[j]), 6),
            })

    out = pd.DataFrame(rows)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROJECT_NEIGHBORS_PATH, index=False)
    log.info(f"Project neighbors: {len(out)} rows -> {PROJECT_NEIGHBORS_PATH}")
    return out


def ensure_project_artifacts() -> tuple:
    """Ensure project_metrics.parquet and project_neighbors.parquet exist; build if needed."""
    if not PROJECTS_PATH.exists():
        build_synthetic_projects()
    if not PROJECT_METRICS_PATH.exists():
        compute_project_metrics()
    if not PROJECT_NEIGHBORS_PATH.exists():
        compute_project_neighbors()
    return pd.read_parquet(PROJECT_METRICS_PATH), pd.read_parquet(PROJECT_NEIGHBORS_PATH)
