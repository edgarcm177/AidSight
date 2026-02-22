"""
Success Twin ML: embed project descriptions and find semantically similar projects
using sentence-transformers/all-MiniLM-L6-v2 and cosine similarity.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# Module-level cache for model and embeddings (lazy-loaded)
_embedding_model: Any = None
_project_embeddings: Optional[np.ndarray] = None
_project_ids: Optional[List[str]] = None
_project_rows: Optional[Dict[str, pd.Series]] = None


def load_embedding_model():
    """
    Load sentence-transformers/all-MiniLM-L6-v2 once and cache it.
    """
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _embedding_model


def embed_projects(df: pd.DataFrame, model=None) -> np.ndarray:
    """
    Return embedding matrix for project descriptions.
    Uses cached model if model is None; otherwise uses provided model.
    """
    if model is None:
        model = load_embedding_model()
    descriptions = df["description"].fillna("").astype(str).tolist()
    return model.encode(descriptions, convert_to_numpy=True)


def _ensure_embeddings_initialized(projects_df: pd.DataFrame) -> None:
    """Lazy-initialize embeddings from projects_df if cache is empty."""
    global _project_embeddings, _project_ids, _project_rows
    if _project_embeddings is not None:
        return

    model = load_embedding_model()
    descriptions = projects_df["description"].fillna("").astype(str).tolist()
    ids = projects_df["id"].astype(str).tolist()

    _project_embeddings = model.encode(descriptions, convert_to_numpy=True)
    _project_ids = ids
    _project_rows = {str(r["id"]): r for _, r in projects_df.iterrows()}


def _build_bullets_from_row(row: pd.Series) -> List[str]:
    """Build 2-3 bullets from twin project row."""
    bullets: List[str] = []

    sector = row.get("sector", "Unknown")
    year = int(row.get("year", 0)) if pd.notna(row.get("year")) else "N/A"
    country = row.get("country", "")
    budget = row.get("budget", 0)
    beneficiaries = row.get("beneficiaries", 0)

    # Budget/beneficiary phrase
    if pd.notna(budget) and pd.notna(beneficiaries) and beneficiaries > 0:
        cost_pb = budget / beneficiaries
        if cost_pb < 50:
            reach = "high beneficiary reach"
        elif cost_pb < 200:
            reach = "medium budget and moderate beneficiary reach"
        else:
            reach = "higher budget, focused delivery"
    else:
        reach = "medium budget and high beneficiary reach"

    bullets.append(f"{sector} project in {country} {year} with {reach}.")

    if "robust_under_shock" in row.index and pd.notna(row.get("robust_under_shock")):
        if row["robust_under_shock"] in (True, "true", "True", 1, "1"):
            bullets.append("Tagged as robust under shock in historical data.")

    if len(bullets) < 2:
        bullets.append("Similar intervention profile for Success Twin matching.")

    return bullets[:3]


def find_success_twin(
    projects_df: pd.DataFrame,
    target_project_id: str,
) -> Dict[str, Any]:
    """
    Find a Success Twin project semantically similar to the target.
    Uses sentence-transformers embeddings and cosine similarity.
    Returns TwinResult-compatible dict with target_project_id, twin_project_id,
    similarity_score (0-1, 3 decimals), and bullets derived from twin row.
    """
    if target_project_id not in projects_df["id"].values:
        raise ValueError("target_project_id not found")

    _ensure_embeddings_initialized(projects_df)

    target_idx = _project_ids.index(str(target_project_id))
    target_emb = _project_embeddings[target_idx : target_idx + 1]
    sims = cosine_similarity(target_emb, _project_embeddings)[0]

    # Exclude target; pick best other (never return self as twin)
    sims[target_idx] = -1.0
    best_idx = int(np.argmax(sims))
    twin_id = _project_ids[best_idx]
    if str(twin_id) == str(target_project_id):
        raise ValueError(
            "No other project available to match as twin (only one project in the set, or twin would be self)"
        )
    score = float(np.clip(sims[best_idx], 0.0, 1.0))

    row = _project_rows[twin_id]
    bullets = _build_bullets_from_row(row)
    twin_name = str(row.get("name", "")) if pd.notna(row.get("name")) else ""
    if not twin_name and (row.get("sector") or row.get("country") or row.get("year")):
        parts = [str(row.get("sector", "")), str(row.get("country", "")), str(int(row.get("year", 0)))]
        twin_name = " ".join(p for p in parts if p).strip() or str(twin_id)

    return {
        "target_project_id": str(target_project_id),
        "twin_project_id": str(twin_id),
        "similarity_score": round(score, 3),
        "bullets": bullets,
        "twin_name": twin_name or str(twin_id),
    }
