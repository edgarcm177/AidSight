#!/usr/bin/env python3
"""
Ingest project embeddings from dataml/data/processed/project_embeddings.parquet
into Actian VectorAI DB so "Similar Projects (VectorAI)" uses the real vector DB.

Prerequisites:
  - ACTIAN_VECTORAI_CONNECTION_STRING, ACTIAN_PROJECTS_COLLECTION set in env
  - VectorAI DB running (e.g. docker compose in actian-vectorAI-db-beta repo)
  - project_embeddings.parquet built (run dataml embeddings pipeline)

Run from repo root:
  python -m backend.scripts.ingest_vectorai_projects
  # or
  python backend/scripts/ingest_vectorai_projects.py
"""
from __future__ import annotations

import os
import sys

# Ensure backend and repo root are on path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_DATAML = os.path.join(_REPO_ROOT, "dataml")
if _DATAML not in sys.path:
    sys.path.insert(0, _DATAML)

BATCH_SIZE = 500


def main() -> int:
    if not os.environ.get("ACTIAN_VECTORAI_CONNECTION_STRING") or not os.environ.get(
        "ACTIAN_PROJECTS_COLLECTION"
    ):
        print(
            "Set ACTIAN_VECTORAI_CONNECTION_STRING and ACTIAN_PROJECTS_COLLECTION.",
            file=sys.stderr,
        )
        return 1

    from backend.clients.vectorai_client import batch_upsert_projects, vectorai_enabled
    from backend.services.vectorai import iter_project_embeddings

    if not vectorai_enabled():
        print("VectorAI client is disabled; check env and actiancortex.", file=sys.stderr)
        return 1

    items = list(iter_project_embeddings())
    if not items:
        print(
            "No project embeddings found. Build dataml/data/processed/project_embeddings.parquet first.",
            file=sys.stderr,
        )
        return 1

    total = 0
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i : i + BATCH_SIZE]
        batch_upsert_projects(batch)
        total += len(batch)
        print(f"Upserted {total}/{len(items)} projects...")

    print(f"Done. Ingested {total} projects into Actian VectorAI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
