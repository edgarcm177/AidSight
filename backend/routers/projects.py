"""Project metrics and neighbors endpoints. Data from dataml/data/processed/."""

import json
import logging
from pathlib import Path
from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException

from ..data import data_loader

router = APIRouter()
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATAML_PROCESSED = REPO_ROOT / "dataml" / "data" / "processed"
PROJECT_METRICS_JSON = DATAML_PROCESSED / "project_metrics.json"
PROJECT_NEIGHBORS_JSON = DATAML_PROCESSED / "project_neighbors.json"

# Country -> region for for_crisis fallback (same region when no project in country). Keep in sync with preprocess.
COUNTRY_TO_REGION = {
    "MLI": "Sahel", "BFA": "Sahel", "NER": "Sahel", "TCD": "Sahel", "NGA": "Sahel",
    "CMR": "Central Africa", "CAF": "Central Africa", "COD": "Central Africa",
    "SSD": "East Africa", "SDN": "East Africa", "ETH": "East Africa", "SOM": "East Africa",
    "SYR": "Middle East", "YEM": "Middle East", "IRQ": "Middle East",
    "AFG": "Asia", "MMR": "Asia", "PAK": "Asia", "UKR": "Europe",
    "HTI": "Latin America", "COL": "Latin America", "VEN": "Latin America",
}


@router.get("/", response_model=List[dict])
def list_projects():
    """
    Return list of projects for Success Twin / similar-projects selector.
    Each item: id, name, sector, country, year, description (so the UI can show human-readable labels).
    """
    df = data_loader.load_projects()
    out = []
    for _, row in df.iterrows():
        pid = str(row.get("id", ""))
        name = str(row.get("name", "")) if pd.notna(row.get("name")) else ""
        sector = str(row.get("sector", "")) if pd.notna(row.get("sector")) else ""
        country = str(row.get("country", "")) if pd.notna(row.get("country")) else ""
        year = int(row.get("year", 0)) if pd.notna(row.get("year")) else 0
        desc = str(row.get("description", "")) if pd.notna(row.get("description")) else ""
        region = str(row.get("region", "")) if pd.notna(row.get("region")) else ""
        out.append({
            "id": pid,
            "name": name,
            "sector": sector,
            "country": country,
            "year": year,
            "region": region,
            "description": desc,
        })
    return out


def _row_to_project(row: pd.Series) -> dict:
    pid = str(row.get("id", ""))
    name = str(row.get("name", "")) if pd.notna(row.get("name")) else ""
    sector = str(row.get("sector", "")) if pd.notna(row.get("sector")) else ""
    cy = str(row.get("country", "")) if pd.notna(row.get("country")) else ""
    yr = int(row.get("year", 0)) if pd.notna(row.get("year")) else 0
    desc = str(row.get("description", "")) if pd.notna(row.get("description")) else ""
    region = str(row.get("region", "")) if pd.notna(row.get("region")) else ""
    return {"id": pid, "name": name, "sector": sector, "country": cy, "year": yr, "description": desc, "region": region}


@router.get("/for_crisis")
def get_project_for_crisis(country: str, year: int | None = None):
    """
    Return a single project for the given crisis (country and optional year).
    Used so Success Twin is driven by the selected epicenter.
    If no project exists for that exact country/year, falls back to:
      1) same year, any country (nearest context)
      2) nearest year (year±1, year±2), same country then any
      3) any project
    Response includes optional fallback and fallback_reason so the UI can explain.
    """
    country = (country or "").strip().upper()
    if not country:
        raise HTTPException(status_code=400, detail="country is required")
    year = int(year) if year is not None else None
    df = data_loader.load_projects()
    df = df.copy()
    df["country_norm"] = df["country"].astype(str).str.upper().str.strip()
    df["year_int"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    # Region: use column if present, else derive from country
    if "region" not in df.columns:
        df["region"] = df["country_norm"].map(COUNTRY_TO_REGION).fillna("")
    else:
        df["region"] = df["region"].astype(str).fillna("")
    request_region = COUNTRY_TO_REGION.get(country, "")

    # 1) Exact: same country, same year (if year given) or any year
    exact = df[df["country_norm"] == country]
    if year is not None:
        exact = exact[exact["year_int"] == year]
    if not exact.empty:
        out = _row_to_project(exact.iloc[0])
        out["fallback"] = False
        return out

    # 2) Same region, same year (nearest context: same region + time)
    if year is not None and request_region:
        same_region_year = df[(df["region"] == request_region) & (df["year_int"] == year)]
        if not same_region_year.empty:
            out = _row_to_project(same_region_year.iloc[0])
            out["fallback"] = True
            out["fallback_reason"] = "same_region"
            return out

    # 3) Same year, any country (nearest context by time)
    if year is not None:
        same_year = df[df["year_int"] == year]
        if not same_year.empty:
            out = _row_to_project(same_year.iloc[0])
            out["fallback"] = True
            out["fallback_reason"] = "no_project_in_country"
            return out

    # 4) Same region, nearest year (year±1, year±2)
    if year is not None and request_region:
        for delta in (1, -1, 2, -2):
            y = year + delta
            same_region = df[(df["region"] == request_region) & (df["year_int"] == y)]
            if not same_region.empty:
                out = _row_to_project(same_region.iloc[0])
                out["fallback"] = True
                out["fallback_reason"] = "same_region"
                return out

    # 5) Nearest year: same country then any
    if year is not None:
        for delta in (1, -1, 2, -2):
            y = year + delta
            same_country = df[(df["country_norm"] == country) & (df["year_int"] == y)]
            if not same_country.empty:
                out = _row_to_project(same_country.iloc[0])
                out["fallback"] = True
                out["fallback_reason"] = "nearest_year"
                return out
        for delta in (1, -1, 2, -2):
            y = year + delta
            any_country = df[df["year_int"] == y]
            if not any_country.empty:
                out = _row_to_project(any_country.iloc[0])
                out["fallback"] = True
                out["fallback_reason"] = "nearest_year"
                return out

    # 6) Same region, any year
    if request_region:
        same_region = df[df["region"] == request_region]
        if not same_region.empty:
            out = _row_to_project(same_region.iloc[0])
            out["fallback"] = True
            out["fallback_reason"] = "same_region"
            return out

    # 7) Any project (last resort)
    if not df.empty:
        out = _row_to_project(df.iloc[0])
        out["fallback"] = True
        out["fallback_reason"] = "no_project_in_country"
        return out

    raise HTTPException(status_code=404, detail="No projects in dataset.")


def _load_project_neighbors() -> list:
    if not PROJECT_NEIGHBORS_JSON.exists():
        raise HTTPException(
            status_code=503,
            detail="project_neighbors.json not found. Run DataML export.",
        )
    with open(PROJECT_NEIGHBORS_JSON) as f:
        return json.load(f)


@router.get("/metrics")
def get_metrics():
    """Return project_metrics.json from DataML."""
    if not PROJECT_METRICS_JSON.exists():
        raise HTTPException(
            status_code=503,
            detail="project_metrics.json not found. Run DataML export.",
        )
    with open(PROJECT_METRICS_JSON) as f:
        return json.load(f)


@router.get("/neighbors/{project_id}")
def get_neighbors_by_project(project_id: str):
    """
    Return neighbors for a single project from project_neighbors.json.
    Returns {"project_id": "...", "neighbors": [...]} or 404 if not found.
    """
    data = _load_project_neighbors()
    for item in data:
        if str(item.get("project_id", "")) == str(project_id):
            return {"project_id": item["project_id"], "neighbors": item.get("neighbors", [])}
    raise HTTPException(status_code=404, detail=f"Project {project_id} not found")


def _normalize_neighbors(raw: list) -> list:
    """Ensure neighbors have id, similarity_score, ratio, country, cluster."""
    out = []
    for r in raw:
        m = r.get("metadata", r)
        out.append({
            "id": r.get("id", r.get("project_id", "")),
            "similarity_score": r.get("similarity_score", r.get("score", 0)),
            "ratio": m.get("ratio_reached", m.get("ratio", 0)),
            "country": m.get("country_iso3", m.get("country", "")),
            "cluster": m.get("cluster", ""),
        })
    return out


@router.get("/{project_id}/vector_neighbors")
def get_vector_neighbors(project_id: str, top_k: int = 5):
    """
    Return similar projects. Uses Actian VectorAI DB when configured; falls back to local KNN otherwise.
    Schema: project_id, neighbors: [{id, similarity_score, ratio, country, cluster}]
    """
    try:
        from ..clients.vectorai_client import VectorAIDisabled, query_similar_projects

        results = query_similar_projects(project_id, top_k)
        log.info("VectorAI neighbors used for project_id=%s (k=%d)", project_id, top_k)
        return {"project_id": project_id, "neighbors": _normalize_neighbors(results)}
    except VectorAIDisabled:
        from ..services.vectorai import search_similar_projects

        results = search_similar_projects(project_id, top_k)
        log.info("VectorAI disabled; using in-memory neighbors for project_id=%s", project_id)
        return {"project_id": project_id, "neighbors": _normalize_neighbors(results)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
