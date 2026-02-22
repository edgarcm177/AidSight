"""
Actian VectorAI preparation: load embeddings from DataML parquet files.
Provides helpers for crisis and project embeddings; can later be swapped for real VectorAI DB.

Expected VectorAI collection schema:
  - id: string (e.g., "MLI-2026" for crises, project_id for projects)
  - embedding: vector<float>
  - metadata: JSON (country, year, severity, underfunding_score, cluster, ratio_reached, etc.)
"""

import logging
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATAML_PROCESSED = REPO_ROOT / "dataml" / "data" / "processed"
CRISIS_EMBEDDINGS = DATAML_PROCESSED / "crisis_embeddings.parquet"
PROJECT_EMBEDDINGS = DATAML_PROCESSED / "project_embeddings.parquet"


def iter_crisis_embeddings() -> Iterator[Dict[str, Any]]:
    """
    Yield crisis embeddings from crisis_embeddings.parquet.
    Each item: {"id": "MLI-2026", "embedding": [...], "metadata": {...}}
    """
    if not CRISIS_EMBEDDINGS.exists():
        logger.warning("crisis_embeddings.parquet not found; skipping")
        return
    try:
        import pandas as pd

        df = pd.read_parquet(CRISIS_EMBEDDINGS)
        for _, row in df.iterrows():
            country = str(row.get("country_iso3", ""))
            year = int(row.get("year", 0))
            doc_id = f"{country}-{year}"
            embedding = row.get("embedding")
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            metadata = {
                "country_iso3": country,
                "year": year,
                "severity": float(row.get("severity", 0)),
                "underfunding_score": float(row.get("underfunding_score", 0)),
                "chronic_underfunded_flag": int(row.get("chronic_underfunded_flag", 0)),
                "description": str(row.get("description", "")),
            }
            yield {"id": doc_id, "embedding": embedding, "metadata": metadata}
    except Exception as e:
        logger.warning("Failed to load crisis_embeddings.parquet: %s", e)


def iter_project_embeddings() -> Iterator[Dict[str, Any]]:
    """
    Yield project embeddings from project_embeddings.parquet.
    Each item: {"id": project_id, "embedding": [...], "metadata": {...}}
    """
    if not PROJECT_EMBEDDINGS.exists():
        logger.warning("project_embeddings.parquet not found; skipping")
        return
    try:
        import pandas as pd

        df = pd.read_parquet(PROJECT_EMBEDDINGS)
        for _, row in df.iterrows():
            project_id = str(row.get("project_id", ""))
            embedding = row.get("embedding")
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            metadata = {
                "country_iso3": str(row.get("country_iso3", "")),
                "year": int(row.get("year", 0)),
                "cluster": str(row.get("cluster", "")),
                "ratio_reached": float(row.get("ratio_reached", 0)),
                "outlier_flag": int(row.get("outlier_flag", 0)),
                "description": str(row.get("description", "")),
            }
            yield {"id": project_id, "embedding": embedding, "metadata": metadata}
    except Exception as e:
        logger.warning("Failed to load project_embeddings.parquet: %s", e)


def _cosine_similarity(a: list, b: list) -> float:
    """Naive cosine similarity (stub for in-memory search when no VectorAI DB)."""
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


def search_similar_crises(country_iso3: str, year: int, top_k: int = 5) -> list:
    """
    OPTIONAL: Naive in-memory cosine-similarity search for crises similar to (country_iso3, year).
    Can later be replaced by real Actian VectorAI.
    """
    target_id = f"{country_iso3}-{year}"
    items = list(iter_crisis_embeddings())
    target = next((x for x in items if x["id"] == target_id), None)
    if not target or not target.get("embedding"):
        return []
    tvec = target["embedding"]
    scored = [
        (x, _cosine_similarity(tvec, x.get("embedding", [])))
        for x in items
        if x["id"] != target_id and x.get("embedding")
    ]
    scored.sort(key=lambda p: p[1], reverse=True)
    return [{"id": p["id"], "metadata": p["metadata"], "score": s} for p, s in scored[:top_k]]


def search_similar_projects(project_id: str, top_k: int = 5) -> list:
    """
    OPTIONAL: Naive in-memory cosine-similarity search for projects similar to project_id.
    Can later be replaced by real Actian VectorAI.
    """
    items = list(iter_project_embeddings())
    target = next((x for x in items if x["id"] == project_id), None)
    if not target or not target.get("embedding"):
        return []
    tvec = target["embedding"]
    scored = [
        (x, _cosine_similarity(tvec, x.get("embedding", [])))
        for x in items
        if x["id"] != project_id and x.get("embedding")
    ]
    scored.sort(key=lambda p: p[1], reverse=True)
    return [{"id": p["id"], "metadata": p["metadata"], "score": s} for p, s in scored[:top_k]]
