"""
Optional VectorAI-style similarity search endpoints.
Uses in-memory stub (iter_crisis_embeddings, iter_project_embeddings) when no Actian DB.
"""

from fastapi import APIRouter

from ..services.vectorai import search_similar_crises, search_similar_projects

router = APIRouter()


@router.get("/similar_crises")
def similar_crises(country_iso3: str, year: int = 2026, top_k: int = 5):
    """
    Find crises similar to (country_iso3, year).
    Stub: in-memory cosine similarity. Replace with Actian VectorAI when available.
    """
    return {"results": search_similar_crises(country_iso3, year, top_k)}


@router.get("/similar_projects")
def similar_projects(project_id: str, top_k: int = 5):
    """
    Find projects similar to project_id.
    Stub: in-memory cosine similarity. Replace with Actian VectorAI when available.
    """
    return {"results": search_similar_projects(project_id, top_k)}
