#!/usr/bin/env python3
"""
Process displacement flow data from IOM DTM.
Primary: dataml/data/raw/global-iom-dtm-from-api-admin-0-to-2.csv
Optional: dataml/data/raw/somalia_dtm-flow-monitoring-dataset-oct-dec-2016.xlsx
Output: dataml/data/processed/flow_edges.csv

Region: Sahel. Only STUB MODE when neither file exists or no Sahel flows.

CLI (run from repo root):
  python -m dataml.scripts.fetch_displacement_flows
  python dataml/scripts/fetch_displacement_flows.py
"""

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dataml.scripts._region_config import SAHEL_ISO3, YEAR_MIN, YEAR_MAX
from dataml.src.graph import SPILLOVER_EDGES

DATAML_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = DATAML_ROOT / "data" / "raw"
PROCESSED_DIR = DATAML_ROOT / "data" / "processed"

# Primary: global IOM DTM
DTM_GLOBAL_CSV = RAW_DIR / "global-iom-dtm-from-api-admin-0-to-2.csv"
# Optional: Somalia DTM Excel
DTM_SOMALIA_XLSX = RAW_DIR / "somalia_dtm-flow-monitoring-dataset-oct-dec-2016.xlsx"

# Pcode prefix (2 chars) -> ISO3 for Sahel
PCODE_PREFIX_TO_ISO3: dict[str, str] = {
    "BF": "BFA", "ML": "MLI", "NE": "NER", "TD": "TCD", "CM": "CMR",
    "NG": "NGA", "SD": "SDN", "SS": "SSD", "CF": "CAF", "CA": "CAF",
    "SN": "SEN", "MR": "MRT", "GM": "GMB", "SO": "SOM", "AF": "AFG",
    "ET": "ETH", "KE": "KEN",
}

log = logging.getLogger(__name__)


def _pcode_to_iso3(pcode: str) -> str:
    """Extract ISO3 from admin pcode (e.g. BF56 -> BFA, NE01 -> NER)."""
    s = str(pcode).strip().upper()
    if len(s) >= 3 and s[:3] in (list(SAHEL_ISO3) + ["COD", "SOM", "AFG"]):
        return s[:3]
    if len(s) >= 2:
        return PCODE_PREFIX_TO_ISO3.get(s[:2], "")
    return ""


def _load_global_dtm() -> "pd.DataFrame | None":
    import pandas as pd

    if not DTM_GLOBAL_CSV.exists():
        return None
    df = pd.read_csv(DTM_GLOBAL_CSV, na_values=["", "null", "NULL", "Not available"])
    # admin0Pcode = destination (where IDPs are), idpOriginAdmin1Pcode = origin
    if "admin0Pcode" not in df.columns:
        return None
    df["dest_iso3"] = df["admin0Pcode"].astype(str).str.upper().str[:3]
    df["origin_iso3"] = df["idpOriginAdmin1Pcode"].astype(str).apply(_pcode_to_iso3)
    # If origin not parsed, use dest (internal flow)
    df.loc[df["origin_iso3"] == "", "origin_iso3"] = df["dest_iso3"]
    df["year"] = pd.to_numeric(df.get("yearReportingDate", df.get("year", 2024)), errors="coerce").fillna(2024).astype("int64")
    flow_col = "numPresentIdpInd" if "numPresentIdpInd" in df.columns else None
    if flow_col is None:
        if "numberMales" in df.columns and "numberFemales" in df.columns:
            df["people_flow"] = pd.to_numeric(df["numberMales"], errors="coerce").fillna(0) + pd.to_numeric(df["numberFemales"], errors="coerce").fillna(0)
        else:
            df["people_flow"] = 1
    else:
        df["people_flow"] = pd.to_numeric(df[flow_col], errors="coerce").fillna(0)
    return df


def _load_somalia_dtm() -> "pd.DataFrame | None":
    import pandas as pd

    if not DTM_SOMALIA_XLSX.exists():
        return None
    try:
        xl = pd.ExcelFile(DTM_SOMALIA_XLSX, engine="openpyxl")
    except Exception:
        return None
    dfs = []
    for sheet in xl.sheet_names[:5]:  # first few sheets
        df = pd.read_excel(xl, sheet_name=sheet, engine="openpyxl")
        if df.empty:
            continue
        # Look for origin/dest/count columns
        cols = [str(c).lower() for c in df.columns]
        dest_col = next((df.columns[i] for i, c in enumerate(cols) if "dest" in c or "admin0" in c or "country" in c), None)
        orig_col = next((df.columns[i] for i, c in enumerate(cols) if "origin" in c or "from" in c), None)
        flow_col = next((df.columns[i] for i, c in enumerate(cols) if "number" in c or "flow" in c or "people" in c), df.columns[0])
        year_col = next((df.columns[i] for i, c in enumerate(cols) if "year" in c or "date" in c), None)
        if dest_col is None:
            df["dest_iso3"] = "SOM"
        else:
            df["dest_iso3"] = df[dest_col].astype(str).str.upper().str[:3]
        if orig_col is None:
            df["origin_iso3"] = "SOM"
        else:
            df["origin_iso3"] = df[orig_col].astype(str).apply(_pcode_to_iso3)
            df.loc[df["origin_iso3"] == "", "origin_iso3"] = "SOM"
        df["year"] = pd.to_numeric(df[year_col] if year_col else 2016, errors="coerce").fillna(2016).astype("int64")
        df["people_flow"] = pd.to_numeric(df[flow_col], errors="coerce").fillna(0)
        dfs.append(df[["origin_iso3", "dest_iso3", "year", "people_flow"]])
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)


def main() -> int:
    import pandas as pd

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    dfs = []
    if DTM_GLOBAL_CSV.exists():
        df = _load_global_dtm()
        if df is not None and not df.empty:
            dfs.append(df)
    if DTM_SOMALIA_XLSX.exists():
        df = _load_somalia_dtm()
        if df is not None and not df.empty:
            dfs.append(df)

    if not dfs:
        log.warning("STUB MODE: Neither DTM file exists; using spillover graph edges")
        rows = [{"origin_iso3": s, "dest_iso3": d, "year": 2024, "people_flow": 1000} for s, d in SPILLOVER_EDGES]
        pd.DataFrame(rows).to_csv(PROCESSED_DIR / "flow_edges.csv", index=False)
        log.info("Wrote %d rows -> flow_edges.csv (stub)", len(rows))
        return 0

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined[(combined["origin_iso3"].str.len() == 3) & (combined["dest_iso3"].str.len() == 3)]
    combined = combined[combined["origin_iso3"].isin(SAHEL_ISO3) | combined["dest_iso3"].isin(SAHEL_ISO3)]
    combined = combined[(combined["year"] >= YEAR_MIN) & (combined["year"] <= YEAR_MAX)]
    out = combined.groupby(["origin_iso3", "dest_iso3", "year"], as_index=False)["people_flow"].sum()
    out["people_flow"] = out["people_flow"].astype("int64")

    if out.empty:
        log.warning("STUB MODE: DTM files have no Sahel flows; using spillover graph")
        rows = [{"origin_iso3": s, "dest_iso3": d, "year": 2024, "people_flow": 1000} for s, d in SPILLOVER_EDGES]
        pd.DataFrame(rows).to_csv(PROCESSED_DIR / "flow_edges.csv", index=False)
        log.info("Wrote %d rows -> flow_edges.csv (stub)", len(rows))
        return 0

    out.to_csv(PROCESSED_DIR / "flow_edges.csv", index=False)
    log.info("Using DTM flows CSV for Sahel 2020-2024 (%d edges).", len(out))
    return 0


if __name__ == "__main__":
    exit(main())
