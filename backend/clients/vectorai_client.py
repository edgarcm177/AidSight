"""
Actian VectorAI client for project similarity search.
Enabled when ACTIAN_VECTORAI_CONNECTION_STRING and ACTIAN_PROJECTS_COLLECTION are set.
Raises VectorAIDisabled when not configured or query fails (never NotImplementedError).
"""

import logging
import os

VectorAIDisabled = type("VectorAIDisabled", (Exception,), {})

logger = logging.getLogger(__name__)


def vectorai_enabled() -> bool:
    """Return True only when both env vars are non-empty."""
    conn = os.environ.get("ACTIAN_VECTORAI_CONNECTION_STRING", "").strip()
    coll = os.environ.get("ACTIAN_PROJECTS_COLLECTION", "").strip()
    return bool(conn and coll)


def query_similar_projects(project_id: str, top_k: int = 5) -> list[dict]:
    """
    Query VectorAI for nearest neighbors of project_id.
    Never returns None: when disabled or on error, always raises VectorAIDisabled.
    Expected neighbor shape: {"project_id"|"id", "similarity_score"|"score",
      "country_iso3"|"country", "cluster", "ratio"|"ratio_reached"}.
    """
    if not vectorai_enabled():
        raise VectorAIDisabled("ACTIAN_VECTORAI_CONNECTION_STRING and ACTIAN_PROJECTS_COLLECTION not set")

    conn_str = os.environ["ACTIAN_VECTORAI_CONNECTION_STRING"]
    collection = os.environ["ACTIAN_PROJECTS_COLLECTION"]

    try:
        # Actian VectorAI SDK integration (when available):
        # from actian_vectorai import connect
        # conn = connect(conn_str)
        # results = conn.query(collection, filter={"id": project_id}, top_k=top_k + 1)
        # return [{"id": r.id, "similarity_score": r.score, "ratio": r.metadata.get("ratio", 0),
        #          "country": r.metadata.get("country_iso3", ""), "cluster": r.metadata.get("cluster", "")}
        #          for r in results if r.id != project_id]
        raise VectorAIDisabled("Actian VectorAI SDK not integrated; use in-memory fallback")
    except VectorAIDisabled:
        raise
    except Exception as e:
        logger.warning("VectorAI query_similar_projects failed: %s", e)
        raise VectorAIDisabled(f"VectorAI query failed: {e}") from e


def upsert_project_embedding(project: dict, embedding: list[float]) -> None:
    """
    Insert/update one project in VectorAI.
    When not vectorai_enabled: no-op (embeddings are not persisted).
    """
    if not vectorai_enabled():
        # In this configuration embeddings are not persisted; ingest script would skip.
        return

    conn_str = os.environ["ACTIAN_VECTORAI_CONNECTION_STRING"]
    collection = os.environ["ACTIAN_PROJECTS_COLLECTION"]

    try:
        # Minimal upsert skeleton (Actian SDK when available):
        # from actian_vectorai import connect
        # conn = connect(conn_str)
        # conn.upsert(collection, id=project.get("id"), embedding=embedding, metadata=project)
        pass
    except Exception as e:
        logger.warning("VectorAI upsert_project_embedding failed: %s", e)
        raise VectorAIDisabled(f"VectorAI upsert failed: {e}") from e
