"""
Preprocessing for Aftershock Sahel panel and spillover graph.

Load raw Sahel CSVs (or filter from HNO/HRP data), build panel (country-year),
construct spillover graph, write dataml/data/processed/*.parquet.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from .graph import SAHEL_ISO3, build_spillover_graph

log = logging.getLogger(__name__)

# Paths relative to dataml/ (parent of src/)
DATAML_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = DATAML_ROOT / "data" / "raw"
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"

YEAR_MIN, YEAR_MAX = 2020, 2026

# Sahel panel source: misfit_final_analysis.csv (HNO/HRP-style)
MISFIT_CSV = RAW_DIR / "misfit_final_analysis.csv"
# Optional explicit spillover edges
SPILLOVER_CSV = RAW_DIR / "spillover_edges.csv"

# Output paths
SAHEL_PANEL_PATH = PROCESSED_DIR / "sahel_panel.parquet"
SPILLOVER_GRAPH_PATH = PROCESSED_DIR / "spillover_graph.parquet"
FEATURES_PATH = PROCESSED_DIR / "features.parquet"


def _coerce_numeric(series: pd.Series) -> pd.Series:
    """Convert series to numeric, treating 'null' and empty as NaN."""
    return pd.to_numeric(
        series.astype(str).replace(["null", "NULL", "", "nan", "NaN"], pd.NA),
        errors="coerce",
    )


def build_sahel_panel(raw_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Build Sahel panel from misfit_final_analysis.csv (or sahel_*.csv).

    Output schema: country_iso3, year, people_in_need, funding_required,
    funding_received, coverage, population, conflict, drought, plus underfunding
    metrics: funding_total_usd, beneficiaries_total, severity, funding_per_beneficiary,
    needs_index, funding_per_need_unit, underfunding_score, chronic_underfunded_flag.
    """
    path = raw_path or MISFIT_CSV
    if not path.exists():
        raise FileNotFoundError(f"Raw CSV not found: {path}")

    df = pd.read_csv(path, na_values=["null", "NULL", "", "nan", "NaN"], low_memory=False)

    # Standardize columns
    df["country_iso3"] = df["Country_ISO3"].astype(str).str.strip().str.upper()
    year_col = "years" if "years" in df.columns else "year"
    df["year"] = _coerce_numeric(df[year_col])
    df["year"] = df["year"].fillna(0).astype("int64")
    df = df[(df["year"] >= YEAR_MIN) & (df["year"] <= YEAR_MAX)]

    # Filter to Sahel region
    df = df[df["country_iso3"].isin(SAHEL_ISO3)]

    # People in need
    df["In_Need"] = _coerce_numeric(df["In_Need"])
    df = df[df["In_Need"].notna() & (df["In_Need"] > 0)]

    # Funding
    df["origRequirements"] = _coerce_numeric(df["origRequirements"])
    df["revisedRequirements"] = _coerce_numeric(df["revisedRequirements"])
    df["funding_per_capita"] = _coerce_numeric(df["funding_per_capita"])
    df["Population"] = _coerce_numeric(df["Population"])

    df["funding_required"] = df["revisedRequirements"].fillna(df["origRequirements"]).fillna(0).clip(lower=0)
    df["funding_received"] = (df["funding_per_capita"].fillna(0) * df["In_Need"]).clip(lower=0)

    # Coverage
    df["coverage"] = 0.0
    mask = (df["funding_required"] > 0) & df["funding_required"].notna()
    df.loc[mask, "coverage"] = df.loc[mask, "funding_received"] / df.loc[mask, "funding_required"]
    df["coverage"] = df["coverage"].clip(0.0, 1.0).fillna(0.0)

    # Population
    pop_median = df["Population"].dropna().median()
    pop_median = pop_median if pop_median and pop_median > 0 else df["In_Need"].median() * 2
    df["population"] = df["Population"].fillna(pop_median).clip(lower=0)

    # Covariates (placeholders: conflict, drought)
    df["conflict"] = 0.2  # placeholder
    df["drought"] = 0.1   # placeholder

    # Dedupe: one row per (country_iso3, year)
    df = df.drop_duplicates(subset=["country_iso3", "year"], keep="first")

    # --- Underfunding metrics (per country-year) ---
    # funding_total_usd: total humanitarian funding received in USD.
    df["funding_total_usd"] = df["funding_received"].astype("float64")
    # beneficiaries_total: people in need (proxy for beneficiaries when not present).
    df["beneficiaries_total"] = df["In_Need"].astype("int64")
    # severity: need_ratio (people_in_need / population) capped [0,1]; higher = more severe.
    df["severity"] = (df["In_Need"] / df["population"].replace(0, 1)).clip(0.0, 1.0).astype("float64")
    # funding_per_beneficiary: funding_total_usd per beneficiary (people in need).
    df["funding_per_beneficiary"] = (
        df["funding_total_usd"] / df["beneficiaries_total"].clip(lower=1)
    ).astype("float64")
    # needs_index: severity * population (need-weighted population metric).
    df["needs_index"] = (df["severity"] * df["population"]).clip(lower=0).astype("float64")
    # funding_per_need_unit: funding per needs_index unit.
    df["funding_per_need_unit"] = (
        df["funding_total_usd"] / df["needs_index"].clip(lower=1)
    ).astype("float64")
    # underfunding_score: 1 minus normalized funding_per_need_unit (higher = more underfunded).
    fpu = df["funding_per_need_unit"]
    fpu_min, fpu_max = fpu.min(), fpu.max()
    fpu_range = max(fpu_max - fpu_min, 1e-9)
    df["underfunding_score"] = (1.0 - (fpu - fpu_min) / fpu_range).astype("float64")
    # chronic_underfunded_flag: 1 if underfunding_score in worst tercile, else 0.
    threshold = df["underfunding_score"].quantile(2.0 / 3.0)
    df["chronic_underfunded_flag"] = (df["underfunding_score"] >= threshold).astype("int64")

    result = pd.DataFrame(
        {
            "country_iso3": df["country_iso3"],
            "year": df["year"],
            "people_in_need": df["In_Need"].astype("int64"),
            "funding_required": df["funding_required"].astype("float64"),
            "funding_received": df["funding_received"].astype("float64"),
            "coverage": df["coverage"].astype("float64"),
            "population": df["population"].astype("float64"),
            "conflict": df["conflict"].astype("float64"),
            "drought": df["drought"].astype("float64"),
            "funding_total_usd": df["funding_total_usd"],
            "beneficiaries_total": df["beneficiaries_total"],
            "severity": df["severity"],
            "funding_per_beneficiary": df["funding_per_beneficiary"],
            "needs_index": df["needs_index"],
            "funding_per_need_unit": df["funding_per_need_unit"],
            "underfunding_score": df["underfunding_score"],
            "chronic_underfunded_flag": df["chronic_underfunded_flag"],
        }
    )

    return result


def build_features(panel_df: pd.DataFrame) -> pd.DataFrame:
    """Derive model-ready features from panel."""
    features = panel_df.copy()
    features["funding_gap_usd"] = features["funding_required"] - features["funding_received"]
    features["funding_gap_usd"] = features["funding_gap_usd"].clip(lower=0)
    features["need_ratio"] = features["people_in_need"] / features["population"].replace(0, 1)
    return features


def main(output_dir: Optional[Path] = None) -> None:
    """
    Run full preprocessing: build panel, graph, features; write parquet.
    """
    out = output_dir or PROCESSED_DIR
    out.mkdir(parents=True, exist_ok=True)

    panel = build_sahel_panel()
    graph = build_spillover_graph(panel)
    features = build_features(panel)

    panel.to_parquet(out / "sahel_panel.parquet", index=False)
    graph.to_parquet(out / "spillover_graph.parquet", index=False)
    features.to_parquet(out / "features.parquet", index=False)

    log.info("Preprocess complete.")
    log.info(f"  Sahel panel:   {len(panel)} rows -> {out / 'sahel_panel.parquet'}")
    log.info(f"  Spillover:     {len(graph)} edges -> {out / 'spillover_graph.parquet'}")
    log.info(f"  Features:      {len(features)} rows -> {out / 'features.parquet'}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
