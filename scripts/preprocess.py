#!/usr/bin/env python3
"""
Preprocess raw CSV data into Parquet tables for AidSight.

Raw crisis input:
  - backend/data/raw/misfit_final_analysis.csv (HNO/HRP-style data with code, Country_ISO3,
    years, In_Need, Population, origRequirements, revisedRequirements, funding_per_capita, etc.)

Output (crises.parquet) key fields:
  - id, name, country, region, severity, people_in_need, funding_required, funding_received,
    coverage, year, population, is_overlooked, funding_missing, population_missing

Imputation philosophy:
  - Minimal but explicit: we prefer 0 with boolean flags over dropping rows.
  - funding_received: 0 when funding_per_capita missing (flag: funding_missing).
  - population: median impute when missing (flag: population_missing).
  - coverage: always in [0, 1]; 0 when funding_required <= 0; never NaN in output.
  - Drop only clearly unusable rows: no ID, no country, no people_in_need.

Run from repo root: python scripts/preprocess.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# Paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "backend" / "data" / "raw"
DATA_DIR = REPO_ROOT / "backend" / "data"

RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

YEAR_MIN, YEAR_MAX = 2020, 2024

MISFIT_CSV = RAW_DIR / "misfit_final_analysis.csv"
PROJECTS_SAMPLE_CSV = RAW_DIR / "projects_sample.csv"
CRISES_PARQUET = DATA_DIR / "crises.parquet"
PROJECTS_PARQUET = DATA_DIR / "projects.parquet"

# Columns core for TTC/Equity: must have no nulls after cleaning
CORE_COLUMNS = ["people_in_need", "funding_required", "funding_received", "coverage"]
# Columns desirable: may be imputed; track with _missing flags
OPTIONAL_COLUMNS = ["population"]

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
log = logging.getLogger(__name__)


def _coerce_numeric(series: pd.Series) -> pd.Series:
    """Convert series to numeric, treating 'null' and empty as NaN."""
    return pd.to_numeric(
        series.astype(str).replace(["null", "NULL", "", "nan", "NaN"], pd.NA),
        errors="coerce",
    )


def _print_null_profile(df: pd.DataFrame, label: str = "Raw CSV") -> None:
    """Print null rates for key columns. Used for inspection."""
    key_cols = [
        "Country_ISO3",
        "Description",
        "code",
        "In_Need",
        "Population",
        "origRequirements",
        "revisedRequirements",
        "funding_per_capita",
    ]
    year_col = "years" if "years" in df.columns else "year"
    if year_col in df.columns:
        key_cols.append(year_col)
    available = [c for c in key_cols if c in df.columns]
    if not available:
        return
    rates = df[available].isna().mean()
    log.info(f"Null profile ({label}, n={len(df)}):")
    for c in available:
        log.info(f"  {c}: {rates[c]:.1%}")
    # Summary comment: core vs incomplete
    # Core for TTC/Equity: In_Need, funding (orig/revised), funding_per_capita, Population
    # Most incomplete: Population (sometimes null), origRequirements/revisedRequirements (0 or null)
    log.info("  Core for TTC/Equity: In_Need, orig/revisedRequirements, funding_per_capita, Population")


def build_crises() -> pd.DataFrame:
    """
    Build crisis-level table from misfit_final_analysis.csv.

    Output schema (matches Crisis Pydantic model):
      id, name, country, region, severity, people_in_need, funding_required,
      funding_received, coverage, year, population, is_overlooked,
      funding_missing, population_missing (flags when imputed)

    Imputation rules (documented for engineers):
      - people_in_need: DROP rows with null or <= 0 (core field)
      - funding_required: revisedRequirements if not null else origRequirements; 0 if both null
      - funding_received: funding_per_capita * In_Need; 0 if funding_per_capita missing (flag funding_missing)
      - coverage: funding_received / funding_required; 0 when denom <= 0; clip to [0, 1]
      - population: impute with median of non-null when missing (flag population_missing)
      - name: if empty, use "Crisis {id} {year}"
      - country/region: "Unknown" if missing (keep ISO3 when available)
    """
    if not MISFIT_CSV.exists():
        raise FileNotFoundError(f"Raw CSV not found: {MISFIT_CSV}")

    df = pd.read_csv(
        MISFIT_CSV,
        na_values=["null", "NULL", "", "nan", "NaN"],
        keep_default_na=True,
        low_memory=False,
    )

    # --- Null profile (before cleaning) ---
    _print_null_profile(df, "misfit_final_analysis.csv (before cleaning)")

    # --- Standardize IDs and keys ---
    id_col = "code" if "code" in df.columns else "id"
    df["_id_raw"] = df[id_col].astype(str).str.strip()
    df["_country_raw"] = df["Country_ISO3"].astype(str).str.strip().str.upper()
    year_col = "years" if "years" in df.columns else "year"
    df["year"] = _coerce_numeric(df[year_col])
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype("int64")
    df = df[df["year"] >= 1900]  # drop invalid years

    # Drop clearly unusable rows: no ID, no country, no needs
    df = df[df["_id_raw"].str.len() > 0]
    df = df[~df["_country_raw"].isin(["", "NAN", "NONE"])]
    df = df.dropna(subset=["Country_ISO3"])
    df["In_Need"] = _coerce_numeric(df["In_Need"])
    df = df[df["In_Need"].notna() & (df["In_Need"] > 0)]

    # Dedupe: one row per (id, year, country), keep first
    df = df.drop_duplicates(subset=["_id_raw", "year", "_country_raw"], keep="first")

    # Filter year window
    df = df[(df["year"] >= YEAR_MIN) & (df["year"] <= YEAR_MAX)]

    # --- Normalize column names to backend expectations ---
    df["origRequirements"] = _coerce_numeric(df["origRequirements"])
    df["revisedRequirements"] = _coerce_numeric(df["revisedRequirements"])
    df["funding_per_capita"] = _coerce_numeric(df["funding_per_capita"])
    df["Population"] = _coerce_numeric(df["Population"])

    # funding_required: revised if not null else orig; 0 if both null
    df["funding_required"] = df["revisedRequirements"].fillna(df["origRequirements"])
    df["funding_required"] = df["funding_required"].fillna(0)
    # Ensure non-negative
    df["funding_required"] = df["funding_required"].clip(lower=0)

    # funding_received: funding_per_capita * In_Need; 0 if funding_per_capita missing
    df["funding_received"] = df["funding_per_capita"].fillna(0) * df["In_Need"]
    df["funding_received"] = df["funding_received"].clip(lower=0)
    funding_missing = df["funding_per_capita"].isna()

    # coverage: funding_received / funding_required; 0 when denom <= 0, clip to [0, 1]
    with pd.option_context("mode.chained_assignment", None):
        df["coverage"] = 0.0
        mask = (df["funding_required"] > 0) & df["funding_required"].notna()
        df.loc[mask, "coverage"] = (
            df.loc[mask, "funding_received"] / df.loc[mask, "funding_required"]
        )
    df["coverage"] = df["coverage"].clip(0.0, 1.0)
    # Replace any remaining NaN (shouldn't happen) with 0
    df["coverage"] = df["coverage"].fillna(0.0)

    # population: impute with median when missing (after all filtering, so df is final)
    pop_median = df["Population"].dropna().median()
    if pd.isna(pop_median) or pop_median <= 0:
        pop_median = df["In_Need"].median() * 2  # fallback
    population_missing = df["Population"].isna()
    df["population"] = df["Population"].fillna(pop_median).clip(lower=0)

    # severity: people_in_need/population rescaled 1-5; default 3.0 if ratio invalid
    ratio = df["In_Need"] / df["population"].replace(0, 1)
    r_min, r_max = ratio.min(), ratio.max()
    if r_max > r_min:
        df["severity"] = 1.0 + 4.0 * (ratio - r_min) / (r_max - r_min)
    else:
        df["severity"] = 3.0
    df["severity"] = df["severity"].clip(1.0, 5.0)

    # region: ISO3 or "Unknown"
    df["country"] = df["_country_raw"].fillna("Unknown").replace("", "Unknown")
    df["region"] = df["country"]

    # name: non-empty; construct "Crisis {id} {year}" if missing
    desc = df["Description"].fillna("").astype(str).str.strip()
    df["name"] = desc.where(desc.str.len() > 0, df["_id_raw"] + " " + df["year"].astype(str))

    # is_overlooked
    iso = df["is_overlooked"]
    if iso.dtype == object or (hasattr(iso.dtype, "name") and iso.dtype.name == "string"):
        df["is_overlooked"] = iso.astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        df["is_overlooked"] = iso.fillna(False).astype(bool)

    # --- Build output DataFrame ---
    crises = pd.DataFrame(
        {
            "id": df["_id_raw"],
            "name": df["name"],
            "country": df["country"],
            "region": df["region"],
            "severity": df["severity"].astype("float64"),
            "people_in_need": df["In_Need"].astype("int64"),
            "funding_required": df["funding_required"].astype("float64"),
            "funding_received": df["funding_received"].astype("float64"),
            "coverage": df["coverage"].astype("float64"),
            "year": df["year"].astype("int64"),
            "population": df["population"].astype("float64"),
            "is_overlooked": df["is_overlooked"],
            "funding_missing": funding_missing.values,
            "population_missing": population_missing.values,
        }
    )

    return crises


def build_projects() -> pd.DataFrame:
    """Build projects table. Uses projects_sample.csv if present, else synthetic data."""
    if PROJECTS_SAMPLE_CSV.exists():
        df = pd.read_csv(PROJECTS_SAMPLE_CSV, na_values=["null", "NULL", ""])
        if (
            "cost_per_beneficiary" not in df.columns
            and "budget" in df.columns
            and "beneficiaries" in df.columns
        ):
            df["cost_per_beneficiary"] = df.apply(
                lambda r: r["budget"] / r["beneficiaries"]
                if r["beneficiaries"] and r["beneficiaries"] > 0
                else float("nan"),
                axis=1,
            )
        return df

    countries = ["AFG", "SYR", "YEM", "SSD", "COD", "SDN", "UKR", "ETH", "SOM", "HTI", "COL", "VEN", "MMR", "NGA"]
    sectors = [
        "Health", "WASH", "Protection", "Food Security",
        "Shelter", "Education", "Nutrition", "Logistics",
    ]
    templates = [
        ("Emergency health services and trauma care for conflict-affected populations.", "Health"),
        ("Water, sanitation, and hygiene promotion in displacement sites.", "WASH"),
        ("Child protection and GBV response in refugee hosting areas.", "Protection"),
        ("Food distribution and cash assistance for food-insecure families.", "Food Security"),
        ("Emergency shelter and NFI kits for IDPs.", "Shelter"),
        ("Temporary learning spaces and teacher training in crisis zones.", "Education"),
        ("CMAM and IYCF support for acutely malnourished children.", "Nutrition"),
        ("Supply chain and warehousing for humanitarian cargo.", "Logistics"),
    ]

    rows = []
    for i, (desc, sector) in enumerate(templates * 2):
        if i >= 25:
            break
        c = countries[i % len(countries)]
        y = 2022 + (i % 3) - 1
        budget = 500_000 + (i * 120_000) % 3_000_000
        beneficiaries = 5_000 + (i * 800) % 50_000
        cost_pb = budget / beneficiaries if beneficiaries > 0 else float("nan")
        rows.append({
            "id": f"PRJ{i+1:03d}",
            "name": f"{sector} project {c} {y}",
            "country": c,
            "year": y,
            "sector": sector,
            "description": desc,
            "budget": float(budget),
            "beneficiaries": int(beneficiaries),
            "cost_per_beneficiary": cost_pb,
            "robust_under_shock": i % 5 == 0,
        })
    return pd.DataFrame(rows)


def _print_status_summary(crises: pd.DataFrame) -> None:
    """Print structured status: total count, imputation rates, per-column null rates (sorted)."""
    log.info("\n--- Preprocess status summary ---")
    log.info(f"Total crises count: {len(crises)}")

    # Imputation rates (share of rows with funding_missing or population_missing)
    pct_funding_imputed = 0.0
    pct_pop_imputed = 0.0
    if "funding_missing" in crises.columns:
        pct_funding_imputed = crises["funding_missing"].mean() * 100.0
    if "population_missing" in crises.columns:
        pct_pop_imputed = crises["population_missing"].mean() * 100.0
    log.info(f"Percentage with imputed funding_received: {pct_funding_imputed:.3f}%")
    log.info(f"Percentage with imputed population: {pct_pop_imputed:.3f}%")

    # Per-column null rates, sorted by null rate (desc), 3 decimal places
    key_cols = ["people_in_need", "funding_required", "funding_received", "coverage", "population"]
    available = [c for c in key_cols if c in crises.columns]
    if available:
        rates = {c: crises[c].isna().mean() * 100.0 for c in available}
        sorted_cols = sorted(rates.keys(), key=lambda x: rates[x], reverse=True)
        log.info("Null rates (column: pct):")
        for c in sorted_cols:
            log.info(f"  {c}: {rates[c]:.3f}%")


def main() -> None:
    crises = build_crises()
    projects = build_projects()

    # Coverage must never be NaN in output (TTC/Equity require valid coverage)
    if crises["coverage"].isna().any():
        nan_count = int(crises["coverage"].isna().sum())
        crises["coverage"] = crises["coverage"].fillna(0.0)
        log.warning(f"Fixed {nan_count} NaN coverage values to 0; coverage must not be NaN.")
    if crises["coverage"].isna().any():
        raise ValueError(
            "coverage column still contains NaN after fillna(0); "
            "check funding_received/funding_required computation."
        )

    crises.to_parquet(CRISES_PARQUET, index=False)
    projects.to_parquet(PROJECTS_PARQUET, index=False)

    log.info("Preprocess complete.")
    log.info(f"  Crises:   {len(crises)} rows -> {CRISES_PARQUET}")
    log.info(f"  Projects: {len(projects)} rows -> {PROJECTS_PARQUET}")
    log.info("\nCrises (first 5):")
    print(crises.head().to_string())
    log.info("\nProjects (first 5):")
    print(projects.head().to_string())

    _print_status_summary(crises)


if __name__ == "__main__":
    main()
