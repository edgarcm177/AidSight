"""Project benchmarking endpoints: /project_metrics, /project_neighbors."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATAML_PROCESSED = REPO_ROOT / "dataml" / "data" / "processed"
PROJECT_METRICS_JSON = DATAML_PROCESSED / "project_metrics.json"
PROJECT_NEIGHBORS_JSON = DATAML_PROCESSED / "project_neighbors.json"


@router.get("/project_metrics")
def get_project_metrics():
    """Return project metrics from dataml/data/processed/project_metrics.json."""
    if not PROJECT_METRICS_JSON.exists():
        raise HTTPException(status_code=503, detail="project_metrics.json not found. Run DataML export.")
    with open(PROJECT_METRICS_JSON) as f:
        return json.load(f)


@router.get("/project_neighbors")
def get_project_neighbors():
    """Return project neighbors from dataml/data/processed/project_neighbors.json."""
    if not PROJECT_NEIGHBORS_JSON.exists():
        raise HTTPException(status_code=503, detail="project_neighbors.json not found. Run DataML export.")
    with open(PROJECT_NEIGHBORS_JSON) as f:
        return json.load(f)
