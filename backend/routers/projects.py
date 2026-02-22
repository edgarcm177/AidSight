"""Project metrics and neighbors endpoints. Data from dataml/data/processed/."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATAML_PROCESSED = REPO_ROOT / "dataml" / "data" / "processed"
PROJECT_METRICS_JSON = DATAML_PROCESSED / "project_metrics.json"
PROJECT_NEIGHBORS_JSON = DATAML_PROCESSED / "project_neighbors.json"


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
        return {"project_id": project_id, "neighbors": _normalize_neighbors(results)}
    except VectorAIDisabled:
        from ..services.vectorai import search_similar_projects

        results = search_similar_projects(project_id, top_k)
        return {"project_id": project_id, "neighbors": _normalize_neighbors(results)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
