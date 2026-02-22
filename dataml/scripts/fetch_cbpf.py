#!/usr/bin/env python3
"""
Fetch CBPF allocations data.
Primary: dataml/data/raw/AllocationsByOrgType__20260222_045216_UTC.csv
Outputs: dataml/data/processed/country_year_funding.csv

Region: Sahel (2020–2024). Only STUB MODE when CSV missing or zero Sahel rows.

CLI (run from repo root):
  python -m dataml.scripts.fetch_cbpf
  python dataml/scripts/fetch_cbpf.py
"""

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dataml.scripts._region_config import SAHEL_ISO3, YEAR_MIN, YEAR_MAX

DATAML_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = DATAML_ROOT / "data" / "raw"
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"

# Primary source: CBPF allocations CSV (no API)
CBPF_ALLOCATIONS_CSV = RAW_DIR / "AllocationsByOrgType__20260222_045216_UTC.csv"

# Map CBPF Name to ISO3 (Sahel-relevant + common)
CBPF_NAME_TO_ISO3: dict[str, str] = {
    "DRC": "COD", "Congo": "COD", "Central African Republic": "CAF", "CAR": "CAF",
    "Sudan": "SDN", "South Sudan": "SSD", "Mali": "MLI", "Niger": "NER",
    "Burkina Faso": "BFA", "Chad": "TCD", "Cameroon": "CMR", "Nigeria": "NGA",
    "Senegal": "SEN", "Mauritania": "MRT", "Gambia": "GMB",
    "Ukraine": "UKR", "Syria": "SYR", "Yemen": "YEM", "Afghanistan": "AFG",
    "Ethiopia": "ETH", "Somalia": "SOM", "Myanmar": "MMR",
}

log = logging.getLogger(__name__)


def main() -> int:
    import pandas as pd

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not CBPF_ALLOCATIONS_CSV.exists():
        # Fallback to misfit only when CSV is missing
        misfit = RAW_DIR / "misfit_final_analysis.csv"
        if misfit.exists():
            log.warning("STUB MODE: Allocations CSV missing; using misfit_final_analysis.csv for Sahel region")
            df = pd.read_csv(misfit, na_values=["null", "NULL", ""])
            df["country_iso3"] = df["Country_ISO3"].astype(str).str.upper()
            year_col = "years" if "years" in df.columns else "year"
            df["year"] = pd.to_numeric(df[year_col], errors="coerce").fillna(YEAR_MAX).astype("int64")
            df = df[df["country_iso3"].isin(SAHEL_ISO3) & (df["year"] >= YEAR_MIN) & (df["year"] <= YEAR_MAX)]
            df = df.drop_duplicates(subset=["country_iso3", "year"])
            agg = df.groupby(["country_iso3", "year"]).agg(
                funding_total_usd=("revisedRequirements", lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum()),
                beneficiaries_total=("In_Need", lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum()),
            ).reset_index()
            agg["projects_count"] = 1
            agg = agg[["country_iso3", "year", "funding_total_usd", "beneficiaries_total", "projects_count"]]
            agg.to_csv(PROCESSED_DIR / "country_year_funding.csv", index=False)
            log.info("Wrote %d rows -> country_year_funding.csv (stub)", len(agg))
            return 0
        log.warning("STUB MODE: Allocations CSV and misfit missing; creating empty outputs")
        pd.DataFrame(columns=["country_iso3", "year", "funding_total_usd", "beneficiaries_total", "projects_count"]).to_csv(
            PROCESSED_DIR / "country_year_funding.csv", index=False
        )
        return 0

    df = pd.read_csv(CBPF_ALLOCATIONS_CSV, na_values=["", "null", "NULL"])
    # Columns: Year, CBPF Name, Total Allocation
    col_year = "Year" if "Year" in df.columns else "year"
    col_name = "CBPF Name" if "CBPF Name" in df.columns else next((c for c in df.columns if "name" in c.lower() or "country" in c.lower()), df.columns[1])
    col_alloc = "Total Allocation" if "Total Allocation" in df.columns else next((c for c in df.columns if "allocation" in c.lower() or "total" in c.lower()), df.columns[2])

    df["year"] = pd.to_numeric(df[col_year], errors="coerce").fillna(0).astype("int64")
    def _name_to_iso3(x: str) -> str:
        s = str(x).strip()
        if s in CBPF_NAME_TO_ISO3:
            return CBPF_NAME_TO_ISO3[s]
        if len(s) >= 3 and s[:3].isalpha():
            return s[:3].upper() if s[:3].upper() in SAHEL_ISO3 else ""
        return ""

    df["country_iso3"] = df[col_name].astype(str).str.strip().apply(_name_to_iso3)
    df["funding_total_usd"] = pd.to_numeric(df[col_alloc], errors="coerce").fillna(0)

    df = df[df["country_iso3"].isin(SAHEL_ISO3) & (df["year"] >= YEAR_MIN) & (df["year"] <= YEAR_MAX)]
    if df.empty:
        # Zero Sahel rows -> STUB
        misfit = RAW_DIR / "misfit_final_analysis.csv"
        if misfit.exists():
            log.warning("STUB MODE: Allocations CSV has no Sahel 2020-2024 rows; using misfit")
            m = pd.read_csv(misfit, na_values=["null", "NULL", ""])
            m["country_iso3"] = m["Country_ISO3"].astype(str).str.upper()
            year_col = "years" if "years" in m.columns else "year"
            m["year"] = pd.to_numeric(m[year_col], errors="coerce").fillna(YEAR_MAX).astype("int64")
            m = m[m["country_iso3"].isin(SAHEL_ISO3) & (m["year"] >= YEAR_MIN) & (m["year"] <= YEAR_MAX)]
            m = m.drop_duplicates(subset=["country_iso3", "year"])
            agg = m.groupby(["country_iso3", "year"]).agg(
                funding_total_usd=("revisedRequirements", lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum()),
                beneficiaries_total=("In_Need", lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum()),
            ).reset_index()
            agg["projects_count"] = 1
            agg[["country_iso3", "year", "funding_total_usd", "beneficiaries_total", "projects_count"]].to_csv(
                PROCESSED_DIR / "country_year_funding.csv", index=False
            )
            log.info("Wrote %d rows -> country_year_funding.csv (stub)", len(agg))
            return 0
        pd.DataFrame(columns=["country_iso3", "year", "funding_total_usd", "beneficiaries_total", "projects_count"]).to_csv(
            PROCESSED_DIR / "country_year_funding.csv", index=False
        )
        return 0

    agg = df.groupby(["country_iso3", "year"]).agg(
        funding_total_usd=("funding_total_usd", "sum"),
        projects_count=("funding_total_usd", "count"),
    ).reset_index()
    agg["beneficiaries_total"] = 0  # allocations CSV has no beneficiaries
    agg = agg[["country_iso3", "year", "funding_total_usd", "beneficiaries_total", "projects_count"]]
    agg["projects_count"] = agg["projects_count"].astype(int)
    agg.to_csv(PROCESSED_DIR / "country_year_funding.csv", index=False)
    log.info("Using CBPF allocations CSV for Sahel 2020-2024 (%d rows).", len(agg))
    return 0


if __name__ == "__main__":
    exit(main())
