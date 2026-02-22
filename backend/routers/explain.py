"""Explain crisis endpoint: Sphinx reasoning copilot."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Optional

router = APIRouter()


class ExplainRequest(BaseModel):
    crisis_id: str
    metrics: dict[str, Any] = {}
    aftershock_totals: Optional[dict[str, Any]] = None


class ExplainResponse(BaseModel):
    explanation: str


@router.post("/crisis", response_model=ExplainResponse)
def explain_crisis_endpoint(payload: ExplainRequest) -> ExplainResponse:
    """
    Explain why this crisis may be overlooked vs neighbors.
    Uses Sphinx if configured; otherwise returns clearly marked fallback stub.
    """
    from ..clients.sphinx_client import SphinxDisabled, explain_crisis

    try:
        text = explain_crisis(
            payload.crisis_id,
            payload.metrics,
            payload.aftershock_totals,
        )
        return ExplainResponse(explanation=text)
    except SphinxDisabled:
        return ExplainResponse(
            explanation="Sphinx is not configured; here is a basic explanation based on local metrics: "
            "The crisis may be overlooked due to lower visibility compared to larger neighboring crises. "
            "Set SPHINX_BASE_URL to enable AI reasoning."
        )
    except Exception as e:
        return ExplainResponse(explanation=f"[Fallback] Could not get explanation: {e}")
