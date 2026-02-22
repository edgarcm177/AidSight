"""Debug endpoints for demos (e.g., Sphinx preview)."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATAML_PROCESSED = REPO_ROOT / "dataml" / "data" / "processed"
SPHINX_TABLES = [
    ("crises_for_sphinx", DATAML_PROCESSED / "crises_for_sphinx.parquet"),
    ("projects_for_sphinx", DATAML_PROCESSED / "projects_for_sphinx.parquet"),
    ("aftershock_baseline_for_sphinx", DATAML_PROCESSED / "aftershock_baseline_for_sphinx.parquet"),
]


@router.get("/sphinx_preview")
def sphinx_preview(n_rows: int = 5):
    """
    Return the first n_rows from each Sphinx-ready Parquet table as JSON.
    Useful for demos; tables may not exist if DataML export hasn't run.
    """
    result = {}
    try:
        import pandas as pd
    except ImportError:
        raise HTTPException(status_code=503, detail="pandas required for sphinx_preview")

    for name, path in SPHINX_TABLES:
        if path.exists():
            df = pd.read_parquet(path)
            result[name] = df.head(n_rows).to_dict(orient="records")
        else:
            result[name] = []

    return result
