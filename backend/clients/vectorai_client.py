"""
Actian VectorAI DB client for project similarity search.
Uses the Actian VectorAI DB beta (actian-vectorAI-db-beta) for nearest-neighbor search.

Enabled when ACTIAN_VECTORAI_CONNECTION_STRING and ACTIAN_PROJECTS_COLLECTION are set.
Raises VectorAIDisabled when not configured or when the SDK is not installed / query fails.
"""

import hashlib
import logging
import os

VectorAIDisabled = type("VectorAIDisabled", (Exception,), {})

logger = logging.getLogger(__name__)

# Default embedding dimension from dataml project embeddings (ratio_reached, underfunding_score, log budget, log beneficiaries, cluster_ord)
DEFAULT_PROJECT_DIMENSION = 5


def _project_id_to_int_id(project_id: str) -> int:
    """Deterministic integer id for VectorAI (Cortex uses int ids)."""
    h = hashlib.sha256(project_id.encode()).hexdigest()[:12]
    return int(h, 16) % (2**31)


def vectorai_enabled() -> bool:
    """Return True only when both env vars are non-empty."""
    conn = os.environ.get("ACTIAN_VECTORAI_CONNECTION_STRING", "").strip()
    coll = os.environ.get("ACTIAN_PROJECTS_COLLECTION", "").strip()
    return bool(conn and coll)


def _get_client():
    """Return a CortexClient instance. Raises VectorAIDisabled if SDK missing or connection fails."""
    try:
        from cortex import CortexClient
    except ImportError as e:
        raise VectorAIDisabled(
            "actiancortex not installed. Install the wheel from "
            "https://github.com/hackmamba-io/actian-vectorAI-db-beta (actiancortex-0.1.0b1-py3-none-any.whl)"
        ) from e

    conn_str = os.environ.get("ACTIAN_VECTORAI_CONNECTION_STRING", "").strip()
    if not conn_str:
        raise VectorAIDisabled("ACTIAN_VECTORAI_CONNECTION_STRING not set")
    return CortexClient(conn_str)


def _ensure_collection(client, collection: str, dimension: int):
    """Create collection if it does not exist (COSINE for normalized embeddings)."""
    try:
        from cortex import DistanceMetric
    except ImportError:
        DistanceMetric = None
    try:
        if not client.has_collection(collection):
            kwargs = {"name": collection, "dimension": dimension}
            if DistanceMetric is not None:
                kwargs["distance_metric"] = DistanceMetric.COSINE
            client.create_collection(**kwargs)
            logger.info("VectorAI collection %s created (dim=%s)", collection, dimension)
    except Exception as e:
        logger.warning("VectorAI ensure collection failed: %s", e)
        raise VectorAIDisabled(f"VectorAI collection setup failed: {e}") from e


def query_similar_projects(project_id: str, top_k: int = 5) -> list[dict]:
    """
    Query Actian VectorAI DB for nearest neighbors of project_id.
    Returns list of dicts with id (project_id), similarity_score, and metadata (country_iso3, cluster, ratio_reached, etc.).
    Raises VectorAIDisabled when not configured or on error.
    """
    if not vectorai_enabled():
        raise VectorAIDisabled("ACTIAN_VECTORAI_CONNECTION_STRING and ACTIAN_PROJECTS_COLLECTION not set")

    collection = os.environ["ACTIAN_PROJECTS_COLLECTION"].strip()
    dimension = int(os.environ.get("ACTIAN_PROJECTS_DIMENSION", DEFAULT_PROJECT_DIMENSION))

    try:
        client = _get_client()
        with client:
            _ensure_collection(client, collection, dimension)
            vid = _project_id_to_int_id(project_id)
            try:
                query_vector, _ = client.get(collection, vid)
            except Exception as e:
                logger.debug("VectorAI get(%s) failed: %s", project_id, e)
                raise VectorAIDisabled(f"Project {project_id} not found in VectorAI DB; run ingestion first") from e

            if not query_vector:
                raise VectorAIDisabled(f"Project {project_id} has no vector in VectorAI DB")
            if hasattr(query_vector, "tolist"):
                query_vector = query_vector.tolist()
            query_vector = list(query_vector)

            k = top_k + 1
            results = client.search(collection, query_vector, top_k=k)

            out = []
            for r in results:
                rid = getattr(r, "id", None)
                payload = getattr(r, "payload", None)
                if payload is None and rid is not None:
                    try:
                        _, payload = client.get(collection, rid)
                    except Exception:
                        payload = {}
                payload = payload or {}
                if not isinstance(payload, dict):
                    payload = {}
                doc_project_id = payload.get("project_id", "")
                if doc_project_id == project_id:
                    continue
                score = getattr(r, "score", 0.0)
                out.append({
                    "id": doc_project_id or str(rid),
                    "project_id": doc_project_id,
                    "similarity_score": float(score),
                    "score": float(score),
                    "metadata": payload,
                })
                if len(out) >= top_k:
                    break
            return out
    except VectorAIDisabled:
        raise
    except Exception as e:
        logger.warning("VectorAI query_similar_projects failed: %s", e)
        raise VectorAIDisabled(f"VectorAI query failed: {e}") from e


def upsert_project_embedding(project_id: str, embedding: list[float], metadata: dict | None = None) -> None:
    """
    Insert or update one project vector in Actian VectorAI DB.
    When not vectorai_enabled(): no-op.
    """
    if not vectorai_enabled():
        return

    collection = os.environ["ACTIAN_PROJECTS_COLLECTION"].strip()
    dimension = int(os.environ.get("ACTIAN_PROJECTS_DIMENSION", DEFAULT_PROJECT_DIMENSION))
    payload = dict(metadata or {})
    payload["project_id"] = project_id

    try:
        client = _get_client()
        with client:
            _ensure_collection(client, collection, dimension)
            vid = _project_id_to_int_id(project_id)
            vec = embedding if len(embedding) == dimension else embedding[:dimension]
            if len(vec) < dimension:
                vec = vec + [0.0] * (dimension - len(vec))
            client.upsert(collection, id=vid, vector=vec, payload=payload)
    except VectorAIDisabled:
        raise
    except Exception as e:
        logger.warning("VectorAI upsert_project_embedding failed: %s", e)
        raise VectorAIDisabled(f"VectorAI upsert failed: {e}") from e


def batch_upsert_projects(items: list[dict]) -> None:
    """
    Batch upsert project embeddings into Actian VectorAI DB.
    Each item: {"id" or "project_id": str, "embedding": list[float], "metadata": dict (optional)}.
    """
    if not vectorai_enabled() or not items:
        return

    collection = os.environ["ACTIAN_PROJECTS_COLLECTION"].strip()
    dimension = int(os.environ.get("ACTIAN_PROJECTS_DIMENSION", DEFAULT_PROJECT_DIMENSION))

    try:
        client = _get_client()
        with client:
            _ensure_collection(client, collection, dimension)
            ids = []
            vectors = []
            payloads = []
            for it in items:
                pid = it.get("project_id", it.get("id", ""))
                emb = it.get("embedding", [])
                meta = dict(it.get("metadata", {}))
                meta["project_id"] = pid
                vec = emb if len(emb) >= dimension else emb + [0.0] * (dimension - len(emb))
                ids.append(_project_id_to_int_id(pid))
                vectors.append(vec[:dimension])
                payloads.append(meta)
            client.batch_upsert(collection, ids, vectors, payloads)
            logger.info("VectorAI batch_upsert %d projects into %s", len(ids), collection)
    except VectorAIDisabled:
        raise
    except Exception as e:
        logger.warning("VectorAI batch_upsert_projects failed: %s", e)
        raise VectorAIDisabled(f"VectorAI batch upsert failed: {e}") from e
