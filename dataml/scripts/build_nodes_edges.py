#!/usr/bin/env python3
"""
Build nodes.json, edges.json, sahel_panel.parquet, spillover_graph.parquet from ETL outputs.
Joins country_year_funding + country_year_severity; uses flow_edges for graph.

Region: Sahel (2020–2024). Artifacts consumed by:
  - GET /status (nodes.json, edges.json)
  - simulate_aftershock (sahel_panel.parquet, spillover_graph.parquet)

Node schema: id/country, year, severity_score, funding_total_usd, beneficiaries_total,
  underfunding_score, funding_per_beneficiary, chronic_underfunded_flag.
Edge schema: source_country, target_country, weight (people_flow for latest year).

CLI (run from repo root, after fetch scripts):
  python -m dataml.scripts.build_nodes_edges
  python dataml/scripts/build_nodes_edges.py
"""

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dataml.scripts._region_config import SAHEL_ISO3, YEAR_MIN, YEAR_MAX, BASELINE_YEAR
from dataml.src.graph import SPILLOVER_EDGES

DATAML_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"

FUNDING_CSV = PROCESSED_DIR / "country_year_funding.csv"
SEVERITY_CSV = PROCESSED_DIR / "country_year_severity.csv"
FLOW_CSV = PROCESSED_DIR / "flow_edges.csv"
NODES_JSON = PROCESSED_DIR / "nodes.json"
EDGES_JSON = PROCESSED_DIR / "edges.json"
SAHEL_PANEL_PATH = PROCESSED_DIR / "sahel_panel.parquet"
SPILLOVER_GRAPH_PATH = PROCESSED_DIR / "spillover_graph.parquet"

log = logging.getLogger(__name__)


def main() -> int:
    import pandas as pd

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Load funding + severity
    if FUNDING_CSV.exists():
        df_funding = pd.read_csv(FUNDING_CSV)
        df_funding = df_funding[df_funding["country_iso3"].isin(SAHEL_ISO3)]
        df_funding["year"] = pd.to_numeric(df_funding["year"], errors="coerce").astype("int64")
        df_funding = df_funding[(df_funding["year"] >= YEAR_MIN) & (df_funding["year"] <= YEAR_MAX)]
    else:
        df_funding = pd.DataFrame(columns=["country_iso3", "year", "funding_total_usd", "beneficiaries_total", "projects_count"])

    if SEVERITY_CSV.exists():
        df_severity = pd.read_csv(SEVERITY_CSV)
        df_severity = df_severity[df_severity["country_iso3"].isin(SAHEL_ISO3)]
        df_severity["year"] = pd.to_numeric(df_severity["year"], errors="coerce").astype("int64")
        df_severity = df_severity[(df_severity["year"] >= YEAR_MIN) & (df_severity["year"] <= YEAR_MAX)]
        if not df_severity.empty:
            sev_min, sev_max = df_severity["severity_score"].min(), df_severity["severity_score"].max()
            log.info("Severity: %d rows, range %.2f-%.2f", len(df_severity), sev_min, sev_max)
    else:
        df_severity = pd.DataFrame(columns=["country_iso3", "year", "severity_score"])

    df = df_funding.copy()
    if not df.empty and not df_severity.empty:
        df = df.merge(df_severity, on=["country_iso3", "year"], how="outer")
    elif not df_severity.empty:
        df = df_severity.copy()

    if df.empty:
        misfit = DATAML_ROOT / "data" / "raw" / "misfit_final_analysis.csv"
        if misfit.exists():
            log.warning("STUB MODE: Processed funding/severity empty; using misfit for Sahel")
            m = pd.read_csv(misfit, na_values=["null", "NULL", ""])
            m["country_iso3"] = m["Country_ISO3"].astype(str).str.upper()
            year_col = "years" if "years" in m.columns else "year"
            m["year"] = pd.to_numeric(m[year_col], errors="coerce").fillna(BASELINE_YEAR).astype("int64")
            m = m[m["country_iso3"].isin(SAHEL_ISO3) & (m["year"] >= YEAR_MIN)]
            m["funding_total_usd"] = pd.to_numeric(m.get("revisedRequirements", m.get("origRequirements", 0)), errors="coerce").fillna(0)
            m["beneficiaries_total"] = pd.to_numeric(m["In_Need"], errors="coerce").fillna(0)
            m["severity_score"] = (m["beneficiaries_total"] / m["Population"].replace(0, 1)).clip(0, 1)
            df = m[["country_iso3", "year", "funding_total_usd", "beneficiaries_total", "severity_score"]].drop_duplicates(["country_iso3", "year"])
        else:
            log.warning("No data; creating empty nodes/edges")
            df = pd.DataFrame(columns=["country_iso3", "year", "funding_total_usd", "beneficiaries_total", "severity_score"])

    df["country"] = df["country_iso3"].astype(str).str.upper()
    df["severity"] = df["severity_score"].fillna(0.5).clip(0, 1) if "severity_score" in df.columns else 0.5
    df["funding_total_usd"] = df["funding_total_usd"].fillna(0) if "funding_total_usd" in df.columns else 0
    df["beneficiaries_total"] = df["beneficiaries_total"].fillna(0).astype("int64") if "beneficiaries_total" in df.columns else 0
    df["funding_per_beneficiary"] = df["funding_total_usd"] / df["beneficiaries_total"].replace(0, 1)
    sev_min, sev_max = df["severity"].min(), df["severity"].max()
    sev_range = (sev_max - sev_min) or 1
    sev_norm = (df["severity"] - sev_min) / sev_range
    fp_min, fp_max = df["funding_per_beneficiary"].min(), df["funding_per_beneficiary"].max()
    fp_range = (fp_max - fp_min) or 1
    fund_norm = (df["funding_per_beneficiary"] - fp_min) / fp_range
    df["underfunding_score"] = (sev_norm * (1 - fund_norm)).clip(0, 1).fillna(0.5)
    df["chronic_underfunded_flag"] = (df["underfunding_score"] > 0.6).astype("int64")

    # nodes.json schema (for GET /status)
    nodes = df[["country", "year", "severity", "funding_total_usd", "beneficiaries_total", "funding_per_beneficiary", "underfunding_score", "chronic_underfunded_flag"]].to_dict("records")
    for n in nodes:
        n["year"] = int(n["year"])
        n["funding_total_usd"] = float(n["funding_total_usd"])
        n["beneficiaries_total"] = float(n["beneficiaries_total"])
        n["funding_per_beneficiary"] = float(n["funding_per_beneficiary"])
        n["underfunding_score"] = round(float(n["underfunding_score"]), 4)
        n["severity"] = round(float(n["severity"]), 4)
        n["severity_score"] = n["severity"]

    with open(NODES_JSON, "w") as f:
        json.dump(nodes, f, indent=2)
    log.info("Wrote %d nodes -> %s (from country_year_funding + country_year_severity)", len(nodes), NODES_JSON)

    # edges.json schema (source_country, target_country, weight)
    latest_year = int(df["year"].max()) if not df.empty else BASELINE_YEAR
    if FLOW_CSV.exists():
        flow = pd.read_csv(FLOW_CSV)
        if "year" in flow.columns and not flow.empty:
            flow_year = int(flow["year"].max())
            flow = flow[flow["year"] == flow_year]
        flow = flow.rename(columns={"origin_iso3": "source_country", "dest_iso3": "target_country"})
        pf = flow["people_flow"] if "people_flow" in flow.columns else 1000
        flow["weight"] = (pf / 1000).clip(0.1, 10)
        edges = flow[["source_country", "target_country", "weight"]].drop_duplicates().to_dict("records")
    else:
        edges = [{"source_country": s, "target_country": d, "weight": 1.0} for s, d in SPILLOVER_EDGES]
    for e in edges:
        e["weight"] = float(e.get("weight", 1))
        e["source"] = e["source_country"]
        e["target"] = e["target_country"]

    with open(EDGES_JSON, "w") as f:
        json.dump(edges, f, indent=2)
    log.info("Wrote %d edges -> %s", len(edges), EDGES_JSON)

    # sahel_panel.parquet + spillover_graph.parquet for simulate_aftershock
    nodes_set = set(df["country_iso3"].unique())
    df["people_in_need"] = df["beneficiaries_total"]
    df["funding_required"] = (df["funding_total_usd"] / 0.5).clip(lower=df["funding_total_usd"])
    df["funding_received"] = df["funding_total_usd"]
    df["coverage"] = (df["funding_received"] / df["funding_required"].replace(0, 1)).clip(0, 1)
    df["population"] = (df["beneficiaries_total"] / df["severity"].replace(0, 0.01)).clip(lower=1e5)
    df["conflict"] = 0.2
    df["drought"] = 0.1
    df["needs_index"] = df["severity"] * df["population"]
    df["funding_per_need_unit"] = df["funding_total_usd"] / df["needs_index"].replace(0, 1)

    panel_cols = [
        "country_iso3", "year", "people_in_need", "funding_required", "funding_received",
        "coverage", "population", "conflict", "drought", "funding_total_usd", "beneficiaries_total",
        "severity", "funding_per_beneficiary", "needs_index", "funding_per_need_unit",
        "underfunding_score", "chronic_underfunded_flag",
    ]
    panel = df[[c for c in panel_cols if c in df.columns]].copy()
    panel.to_parquet(SAHEL_PANEL_PATH, index=False)
    log.info("Wrote sahel_panel.parquet (%d rows) -> %s", len(panel), SAHEL_PANEL_PATH)

    graph_rows = []
    for s, d in SPILLOVER_EDGES:
        if s in nodes_set and d in nodes_set:
            graph_rows.append({"source_iso3": s, "target_iso3": d, "weight": 1.0})
    graph_df = pd.DataFrame(graph_rows)
    graph_df.to_parquet(SPILLOVER_GRAPH_PATH, index=False)
    log.info("Wrote spillover_graph.parquet (%d edges) -> %s", len(graph_df), SPILLOVER_GRAPH_PATH)

    return 0


if __name__ == "__main__":
    exit(main())
