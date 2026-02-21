"""Vector service interface for Actian VectorAI DB."""

import logging
import os
from abc import ABC, abstractmethod
from typing import List

from models import ComparableTrade, Project

logger = logging.getLogger(__name__)


class VectorService(ABC):
    """Abstract interface for vector similarity search."""

    @abstractmethod
    def upsert_vectors(
        self,
        project_id: str,
        text: str,
        metadata: dict,
    ) -> bool:
        pass

    @abstractmethod
    def query_similar(
        self,
        text: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> List[ComparableTrade]:
        pass


class FakeVectorService(VectorService):
    """In-memory fake implementation returning deterministic placeholder results."""

    def __init__(self, projects: List[Project]):
        self.projects = {p.project_id: p for p in projects}

    def upsert_vectors(
        self,
        project_id: str,
        text: str,
        metadata: dict,
    ) -> bool:
        return True

    def query_similar(
        self,
        text: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> List[ComparableTrade]:
        # Return projects from same sector or nearby regions with fake similarity
        projects = list(self.projects.values())[: top_k + 5]
        results: List[ComparableTrade] = []
        for i, p in enumerate(projects[:top_k]):
            sim = max(0.5, 0.95 - i * 0.08)
            results.append(
                ComparableTrade(
                    project_id=p.project_id,
                    title=p.title,
                    similarity=round(sim, 2),
                    key_reasons=[
                        f"Similar sector: {p.sector}",
                        f"Comparable budget: ${p.budget:,.0f}",
                        f"Serves {p.beneficiaries:,} beneficiaries",
                    ],
                    peer_metrics_summary={"budget": p.budget, "beneficiaries": p.beneficiaries},
                )
            )
        return results[:top_k]


class RealActianVectorClient(VectorService):
    """Skeleton for real Actian VectorAI HTTP client."""

    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    def upsert_vectors(
        self,
        project_id: str,
        text: str,
        metadata: dict,
    ) -> bool:
        # TODO: POST to Actian upsert endpoint
        raise NotImplementedError("Actian client not implemented")

    def query_similar(
        self,
        text: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> List[ComparableTrade]:
        # TODO: POST to Actian query endpoint, map response to ComparableTrade
        raise NotImplementedError("Actian client not implemented")


def get_vector_service(projects: List[Project]) -> VectorService:
    """Factory: use real client if env set, else fake."""
    endpoint = os.getenv("ACTIAN_ENDPOINT", "").strip()
    api_key = os.getenv("ACTIAN_API_KEY", "").strip()
    if endpoint and api_key:
        return RealActianVectorClient(endpoint, api_key)
    logger.warning("ACTIAN_ENDPOINT/ACTIAN_API_KEY not set; using FakeVectorService")
    return FakeVectorService(projects)
