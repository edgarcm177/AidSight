#!/usr/bin/env python3
"""
Export flat Parquet tables for Sphinx / Databricks.

Loads from existing parquets and writes clean, concise schemas that Sphinx/Databricks
can query for "why is this crisis overlooked?" reasoning.
Run from repo root: python -m dataml.scripts.export_sphinx_tables
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

DATAML_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"

SAHEL_PANEL_PATH = PROCESSED_DIR / "sahel_panel.parquet"
PROJECT_METRICS_PATH = PROCESSED_DIR / "project_metrics.parquet"
BASELINE_PREDICTIONS_PATH = PROCESSED_DIR / "baseline_predictions.json"

CRISES_FOR_SPHINX_PATH = PROCESSED_DIR / "crises_for_sphinx.parquet"
PROJECTS_FOR_SPHINX_PATH = PROCESSED_DIR / "projects_for_sphinx.parquet"
AFTERSHOCK_BASELINE_FOR_SPHINX_PATH = PROCESSED_DIR / "aftershock_baseline_for_sphinx.parquet"


def main() -> int:
    import pandas as pd

    if not SAHEL_PANEL_PATH.exists():
        print(f"Error: Panel not found: {SAHEL_PANEL_PATH}. Run preprocess first.")
        return 1

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Build embeddings for Actian VectorAI (if not already present)
    from dataml.src import embeddings
    try:
        embeddings.build_crisis_embeddings()
    except Exception as e:
        print(f"Note: crisis_embeddings: {e}")
    try:
        if PROJECT_METRICS_PATH.exists():
            embeddings.build_project_embeddings()
    except Exception as e:
        print(f"Note: project_embeddings: {e}")

    # crises_for_sphinx.parquet
    panel = pd.read_parquet(SAHEL_PANEL_PATH)
    extra_cols = [c for c in panel.columns if c not in {
        "country_iso3", "year", "severity", "funding_total_usd", "needs_index",
        "underfunding_score", "chronic_underfunded_flag"
    }]
    crises = panel[["country_iso3", "year", "severity", "funding_total_usd", "needs_index",
                    "underfunding_score", "chronic_underfunded_flag"]].copy()
    if extra_cols:
        crises["extra_fields_json"] = panel[extra_cols].apply(
            lambda r: json.dumps(r.dropna().to_dict(), default=str),
            axis=1,
        )
    else:
        crises["extra_fields_json"] = None
    crises.to_parquet(CRISES_FOR_SPHINX_PATH, index=False)
    print(f"Exported crises_for_sphinx: {len(crises)} rows -> {CRISES_FOR_SPHINX_PATH}")

    # projects_for_sphinx.parquet
    if PROJECT_METRICS_PATH.exists():
        pm = pd.read_parquet(PROJECT_METRICS_PATH)
        projects = pm[["project_id", "country_iso3", "year", "cluster", "budget_usd",
                       "beneficiaries", "ratio_reached", "outlier_flag"]].copy()
        projects.to_parquet(PROJECTS_FOR_SPHINX_PATH, index=False)
        print(f"Exported projects_for_sphinx: {len(projects)} rows -> {PROJECTS_FOR_SPHINX_PATH}")
    else:
        print("Warning: project_metrics.parquet not found. Run export_project_benchmarking first.")

    # aftershock_baseline_for_sphinx.parquet
    if BASELINE_PREDICTIONS_PATH.exists():
        with open(BASELINE_PREDICTIONS_PATH) as f:
            baseline = json.load(f)
        df_baseline = pd.DataFrame(baseline)
        df_baseline = df_baseline.rename(columns={"country": "country_iso3"})
        df_baseline = df_baseline[["country_iso3", "baseline_year", "severity_pred_baseline", "displacement_in_pred_baseline"]]
        df_baseline.to_parquet(AFTERSHOCK_BASELINE_FOR_SPHINX_PATH, index=False)
        print(f"Exported aftershock_baseline_for_sphinx: {len(df_baseline)} rows -> {AFTERSHOCK_BASELINE_FOR_SPHINX_PATH}")
    else:
        print("Warning: baseline_predictions.json not found. Run export_baseline_structures first.")

    return 0


if __name__ == "__main__":
    exit(main())
