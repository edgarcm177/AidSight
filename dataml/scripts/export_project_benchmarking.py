#!/usr/bin/env python3
"""
Export project_metrics.json and project_neighbors.json for the frontend.

Loads project_metrics.parquet and project_neighbors.parquet (building them from
synthetic projects if missing). Writes JSON files to dataml/data/processed/.
Run from repo root: python -m dataml.scripts.export_project_benchmarking
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

DATAML_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"

PROJECT_METRICS_JSON_PATH = PROCESSED_DIR / "project_metrics.json"
PROJECT_NEIGHBORS_JSON_PATH = PROCESSED_DIR / "project_neighbors.json"


def main() -> int:
    from dataml.src.projects import ensure_project_artifacts

    metrics_df, neighbors_df = ensure_project_artifacts()

    # project_metrics.json: list of dicts
    metrics_list = []
    for _, row in metrics_df.iterrows():
        metrics_list.append({
            "project_id": str(row["project_id"]),
            "country_iso3": str(row["country_iso3"]),
            "year": int(row["year"]),
            "cluster": str(row["cluster"]),
            "budget_usd": round(float(row["budget_usd"]), 0),
            "beneficiaries": int(row["beneficiaries"]),
            "ratio_reached": round(float(row["ratio_reached"]), 6),
            "outlier_flag": str(row["outlier_flag"]),
        })

    # project_neighbors.json: list of {project_id, neighbors: [{neighbor_id, similarity_score, neighbor_ratio_reached}]}
    neighbors_by_project = neighbors_df.groupby("project_id")
    neighbors_list = []
    for pid, grp in neighbors_by_project:
        nb_list = [
            {
                "neighbor_id": str(r["neighbor_id"]),
                "similarity_score": round(float(r["similarity_score"]), 4),
                "neighbor_ratio_reached": round(float(r["neighbor_ratio_reached"]), 6),
            }
            for _, r in grp.iterrows()
        ]
        neighbors_list.append({"project_id": str(pid), "neighbors": nb_list})

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROJECT_METRICS_JSON_PATH, "w") as f:
        json.dump(metrics_list, f, indent=2)
    with open(PROJECT_NEIGHBORS_JSON_PATH, "w") as f:
        json.dump(neighbors_list, f, indent=2)

    print(f"Exported {len(metrics_list)} project metrics -> {PROJECT_METRICS_JSON_PATH}")
    print(f"Exported {len(neighbors_list)} project neighbors -> {PROJECT_NEIGHBORS_JSON_PATH}")
    return 0


if __name__ == "__main__":
    exit(main())
