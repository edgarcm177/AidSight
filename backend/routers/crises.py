import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from typing import List

from ..models import Crisis
from ..data import data_loader

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATAML_PROCESSED = REPO_ROOT / "dataml" / "data" / "processed"
NODES_JSON = DATAML_PROCESSED / "nodes.json"
EDGES_JSON = DATAML_PROCESSED / "edges.json"
BASELINE_JSON = DATAML_PROCESSED / "baseline_predictions.json"

_crises_df = data_loader.load_crises()


def _load_json(path: Path):
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"{path.name} not found. Run DataML export.")
    with open(path) as f:
        return json.load(f)


@router.get("/nodes")
def get_nodes():
    """Return nodes.json from DataML (per-country baseline snapshot)."""
    return _load_json(NODES_JSON)


@router.get("/edges")
def get_edges():
    """Return edges.json from DataML (crisis graph edges)."""
    return _load_json(EDGES_JSON)


@router.get("/baseline_predictions")
def get_baseline_predictions():
    """Return baseline_predictions.json from DataML (no-shock predictions per country)."""
    return _load_json(BASELINE_JSON)


@router.get("/", response_model=List[Crisis])
def list_crises():
    return _crises_df.to_dict(orient="records")


@router.get("/{crisis_id}", response_model=Crisis)
def get_crisis(crisis_id: str):
    row = _crises_df.loc[_crises_df["id"] == crisis_id].iloc[0]
    return row.to_dict()
