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


def build_bullets_from_row(row: pd.Series) -> List[str]:
    """Build 2-3 insight bullets from a project row. Public for reuse (e.g. Similar Projects)."""
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
    restrict_to_country: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find a Success Twin project semantically similar to the target.
    Uses sentence-transformers embeddings and cosine similarity.
    If restrict_to_country is set, the twin is chosen only among projects
    in that country (crisis-matched set).
    Returns TwinResult-compatible dict with target_project_id, twin_project_id,
    similarity_score (0-1, 3 decimals), and bullets derived from twin row.
    """
    if target_project_id not in projects_df["id"].values:
        raise ValueError("target_project_id not found")

    _ensure_embeddings_initialized(projects_df)

    target_idx = _project_ids.index(str(target_project_id))
    target_emb = _project_embeddings[target_idx : target_idx + 1]
    sims = cosine_similarity(target_emb, _project_embeddings)[0]

    # Exclude target; optionally restrict to same country (crisis-matched set)
    sims[target_idx] = -1.0
    if restrict_to_country is not None:
        country_upper = str(restrict_to_country).strip().upper()
        for i, pid in enumerate(_project_ids):
            if i == target_idx:
                continue
            row = _project_rows.get(pid)
            if row is None:
                sims[i] = -1.0
                continue
            proj_country = str(row.get("country", "")).strip().upper()
            if proj_country != country_upper:
                sims[i] = -1.0
    best_idx = int(np.argmax(sims))
    if sims[best_idx] < 0:
        raise ValueError(
            "No twin found in the crisis-matched set (need at least two projects in this country)."
        )
    twin_id = _project_ids[best_idx]
    score = float(np.clip(sims[best_idx], 0.0, 1.0))

    row = _project_rows[twin_id]
    bullets = build_bullets_from_row(row)
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


def find_success_twin_for_epicenter(
    projects_df: pd.DataFrame,
    epicenter: str,
) -> Dict[str, Any]:
    """
    Find a Success Twin for the selected crisis (epicenter).
    Uses the project set matching the crisis (same country), picks a reference
    project from that set, then finds a twin within the same set.
    If the crisis country has only one project, falls back to finding a twin
    in the full project set and adds a note in bullets.
    """
    epicenter_upper = str(epicenter).strip().upper()
    if not epicenter_upper:
        raise ValueError("epicenter is required")

    # Crisis-matched projects: same country as epicenter
    country_col = projects_df["country"].astype(str).str.strip().str.upper()
    subset = projects_df[country_col == epicenter_upper]
    if subset is None or len(subset) == 0:
        raise ValueError(
            f"No projects in crisis country {epicenter_upper}. Add project data for this country (e.g. run backend/scripts/seed_epicenter_projects.py)."
        )

    # Reference project: first by id for deterministic behavior
    reference_row = subset.sort_values("id").iloc[0]
    reference_id = str(reference_row["id"])

    if len(subset) >= 2:
        return find_success_twin(
            projects_df,
            reference_id,
            restrict_to_country=epicenter_upper,
        )

    # Fallback: only one project in crisis country — find twin globally and add a note
    result = find_success_twin(projects_df, reference_id, restrict_to_country=None)
    bullets = list(result.get("bullets", []))
    bullets.append("Twin from global set (only one project in this crisis country; add more for country-specific matching).")
    result["bullets"] = bullets
    return result
