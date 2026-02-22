#!/usr/bin/env python3
"""
Fetch INFORM Severity Index data.
Primary: dataml/data/raw/202601_INFORM_Severity_-_January_2026.xlsx
Output: dataml/data/processed/country_year_severity.csv

Region: Sahel (2020–2024). Uses sheet "INFORM Severity - country" with ISO3 and INFORM Severity Index.
No year column in Excel → uses year=2024 as proxy (Jan 2026 snapshot for 2024 compatibility).
Only STUB MODE when Excel missing or zero Sahel rows.

CLI (run from repo root):
  python -m dataml.scripts.fetch_inform_severity
  python dataml/scripts/fetch_inform_severity.py
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

# Primary: INFORM Severity Excel (Jan 2026 release)
INFORM_EXCEL = RAW_DIR / "202601_INFORM_Severity_-_January_2026.xlsx"
INFORM_SHEET = "INFORM Severity - country"
# Fallback: CSV export if Excel parsing fails
INFORM_CSV = RAW_DIR / "inform_severity.csv"

# Year used when Excel has no year column (Jan 2026 snapshot as proxy for 2024)
INFORM_YEAR_PROXY = 2024

log = logging.getLogger(__name__)


def _read_inform_excel() -> "pd.DataFrame | None":
    """
    Read INFORM Excel sheet "INFORM Severity - country".
    Columns: ISO3, INFORM Severity Index (1-5 scale).
    Returns DataFrame with country_iso3, year, severity_score or None.
    """
    import pandas as pd

    try:
        df = pd.read_excel(
            INFORM_EXCEL,
            sheet_name=INFORM_SHEET,
            engine="openpyxl",
            header=1,  # Header row; row 0 is title, rows 2-3 are metadata
        )
    except ImportError:
        log.warning("openpyxl not installed; pip install openpyxl for Excel support")
        return None
    except Exception as e:
        log.debug("Excel read failed: %s", e)
        return None

    if df.empty or "ISO3" not in df.columns:
        return None

    col_sev = "INFORM Severity Index"
    if col_sev not in df.columns:
        col_sev = next((c for c in df.columns if "severity" in str(c).lower() and "index" in str(c).lower()), None)
        if col_sev is None:
            return None

    df["country_iso3"] = df["ISO3"].astype(str).str.upper().str.strip()
    df["severity_score"] = pd.to_numeric(df[col_sev], errors="coerce")
    df = df[df["country_iso3"].notna() & df["severity_score"].notna()]
    df = df[df["country_iso3"].str.len() == 3]
    df = df[df["country_iso3"].str.match(r"^[A-Z]{3}$", na=False)]

    # INFORM Severity Index is 1-5; normalize to 0-1 for compatibility with build_nodes_edges
    df["severity_score"] = ((df["severity_score"] - 1) / 4).clip(0, 1)
    # No year in sheet; use proxy for 2020-2024 compatibility
    df["year"] = INFORM_YEAR_PROXY

    return df[["country_iso3", "year", "severity_score"]]


def main() -> int:
    import pandas as pd

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Primary: INFORM Excel
    if INFORM_EXCEL.exists():
        df = _read_inform_excel()
        if df is not None and not df.empty:
            out = df[df["country_iso3"].isin(SAHEL_ISO3)]
            out = out[["country_iso3", "year", "severity_score"]].drop_duplicates(subset=["country_iso3", "year"])
            if not out.empty:
                out.to_csv(PROCESSED_DIR / "country_year_severity.csv", index=False)
                log.info("Using INFORM Severity Excel for Sahel 2020-2024 (%d rows).", len(out))
                return 0

    # Fallback: INFORM CSV (if present)
    if INFORM_CSV.exists():
        df = pd.read_csv(INFORM_CSV, na_values=["", "null", "NULL"])
        col_iso = next((c for c in ["iso3", "country_iso3", "ISO3"] if c in df.columns), df.columns[0])
        col_yr = next((c for c in ["year", "Year"] if c in df.columns), "year")
        col_sev = next((c for c in ["severity_score", "severity", "Score"] if c in df.columns), df.columns[2] if len(df.columns) > 2 else df.columns[0])
        df["country_iso3"] = df[col_iso].astype(str).str.upper().str[:3]
        df["year"] = pd.to_numeric(df[col_yr], errors="coerce").fillna(INFORM_YEAR_PROXY).astype("int64")
        df["severity_score"] = pd.to_numeric(df[col_sev], errors="coerce").fillna(0.5)
        out = df[(df["country_iso3"].str.len() == 3) & df["country_iso3"].isin(SAHEL_ISO3) & (df["year"] >= YEAR_MIN) & (df["year"] <= YEAR_MAX)]
        out = out[["country_iso3", "year", "severity_score"]].drop_duplicates(subset=["country_iso3", "year"])
        if not out.empty:
            out.to_csv(PROCESSED_DIR / "country_year_severity.csv", index=False)
            log.info("Using INFORM Severity CSV for Sahel 2020-2024 (%d rows).", len(out))
            return 0

    # STUB: misfit (only when Excel missing or zero Sahel rows)
    misfit = RAW_DIR / "misfit_final_analysis.csv"
    if misfit.exists():
        log.warning("STUB MODE: INFORM Excel missing or no Sahel rows; deriving from misfit")
        df = pd.read_csv(misfit, na_values=["null", "NULL", ""])
        df["country_iso3"] = df["Country_ISO3"].astype(str).str.upper()
        year_col = "years" if "years" in df.columns else "year"
        df["year"] = pd.to_numeric(df[year_col], errors="coerce").fillna(0).astype("int64")
        df["In_Need"] = pd.to_numeric(df["In_Need"], errors="coerce").fillna(0)
        df["Population"] = pd.to_numeric(df["Population"], errors="coerce").fillna(1)
        df["severity_score"] = (df["In_Need"] / df["Population"].replace(0, 1)).clip(0, 1).fillna(0.5)
        out = df[df["country_iso3"].isin(SAHEL_ISO3) & (df["year"] >= YEAR_MIN)]
        out = out[["country_iso3", "year", "severity_score"]].drop_duplicates(subset=["country_iso3", "year"])
        out.to_csv(PROCESSED_DIR / "country_year_severity.csv", index=False)
        log.info("Wrote %d rows -> country_year_severity.csv (stub)", len(out))
        return 0

    log.warning("STUB MODE: No INFORM or misfit; creating empty country_year_severity.csv")
    pd.DataFrame(columns=["country_iso3", "year", "severity_score"]).to_csv(
        PROCESSED_DIR / "country_year_severity.csv", index=False
    )
    return 0


if __name__ == "__main__":
    exit(main())
