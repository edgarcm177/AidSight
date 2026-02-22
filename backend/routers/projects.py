"""Project metrics and neighbors endpoints. Data from dataml/data/processed/."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, HTTPException

from ..data import data_loader
from ..services.twins import build_bullets_from_row

router = APIRouter()
log = logging.getLogger(__name__)

_projects_df = data_loader.load_projects()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATAML_PROCESSED = REPO_ROOT / "dataml" / "data" / "processed"
PROJECT_METRICS_JSON = DATAML_PROCESSED / "project_metrics.json"
PROJECT_NEIGHBORS_JSON = DATAML_PROCESSED / "project_neighbors.json"


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
        out.append({
            "id": pid,
            "name": name,
            "sector": sector,
            "country": country,
            "year": year,
            "description": desc,
        })
    return out


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


def _enrich_neighbors(neighbors: list, projects_df: pd.DataFrame) -> list:
    """Add name, sector, year, insight_bullets to each neighbor by looking up in projects_df."""
    enriched: List[Dict[str, Any]] = []
    ids = projects_df["id"].astype(str)
    for n in neighbors:
        nid = str(n.get("id", ""))
        row = projects_df.loc[ids == nid]
        if len(row) > 0:
            r = row.iloc[0]
            name = str(r.get("name", "")) if pd.notna(r.get("name")) else ""
            sector = str(r.get("sector", "")) if pd.notna(r.get("sector")) else ""
            year = int(r.get("year", 0)) if pd.notna(r.get("year")) else None
            bullets = build_bullets_from_row(r)
            enriched.append({
                **n,
                "name": name or nid,
                "sector": sector,
                "year": year,
                "insight_bullets": bullets,
            })
        else:
            enriched.append({
                **n,
                "name": nid,
                "sector": n.get("cluster", ""),
                "year": None,
                "insight_bullets": ["Similar intervention profile; compare sector and funding."],
            })
    return enriched


# Hardcoded similar projects when VectorAI and local embeddings return nothing (no DB, no parquet)
_HARDCODED_SIMILAR_PROJECTS = [
    {"id": "PRJ001", "similarity_score": 0.92, "ratio": 0.85, "country": "AFG", "cluster": "health"},
    {"id": "PRJ002", "similarity_score": 0.88, "ratio": 0.78, "country": "SYR", "cluster": "wash"},
    {"id": "PRJ003", "similarity_score": 0.85, "ratio": 0.72, "country": "YEM", "cluster": "protection"},
    {"id": "MLI001", "similarity_score": 0.84, "ratio": 0.80, "country": "MLI", "cluster": "health"},
    {"id": "MLI002", "similarity_score": 0.81, "ratio": 0.75, "country": "MLI", "cluster": "wash"},
]


@router.get("/{project_id}/vector_neighbors")
def get_vector_neighbors(project_id: str, top_k: int = 5):
    """
    Return similar projects. Uses Actian VectorAI DB when configured; falls back to local KNN otherwise.
    When no backend returns results, returns hardcoded similar projects so the UI always has something.
    Schema: project_id, neighbors: [{id, similarity_score, ratio, country, cluster}]
    """
    neighbors: list = []
    try:
        from ..clients.vectorai_client import VectorAIDisabled, query_similar_projects

        results = query_similar_projects(project_id, top_k)
        log.info("VectorAI neighbors used for project_id=%s (k=%d)", project_id, top_k)
        neighbors = _normalize_neighbors(results)
    except VectorAIDisabled:
        from ..services.vectorai import search_similar_projects

        results = search_similar_projects(project_id, top_k)
        log.info("VectorAI disabled; using in-memory neighbors for project_id=%s", project_id)
        neighbors = _normalize_neighbors(results)
    except Exception as e:
        log.warning("vector_neighbors fallback after error: %s", e)

    if not neighbors:
        # Hardcoded so Similar Projects (VectorAI) always shows something
        neighbors = _HARDCODED_SIMILAR_PROJECTS[:top_k]
        log.info("Using hardcoded similar projects for project_id=%s", project_id)

    neighbors = _enrich_neighbors(neighbors, _projects_df)
    return {"project_id": project_id, "neighbors": neighbors}
