"""Explain crisis endpoint: Gemini LLM with Sphinx prompt."""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any

router = APIRouter()

# Ensure .env.local is loaded in this process (helps with uvicorn workers / reload)
_env_local = Path(__file__).resolve().parents[2] / ".env.local"
if _env_local.exists():
    load_dotenv(_env_local, override=True)


class ExplainRequest(BaseModel):
    query: str
    context: dict[str, Any] = {}


class ExplainResponse(BaseModel):
    answer: str


@router.post("/crisis", response_model=ExplainResponse)
def explain_crisis_endpoint(body: ExplainRequest) -> ExplainResponse:
    """
    Explain crisis via Gemini using Sphinx prompt.
    Expects body.query and body.context with crisis and aftershock_totals.
    Frontend and API contract unchanged.
    """
    from ..clients.gemini_client import (
        GeminiDisabled,
        GeminiError,
        explain_crisis_via_gemini,
    )

    crisis = body.context.get("crisis", {})
    totals = body.context.get("aftershock_totals", {})

    try:
        answer = explain_crisis_via_gemini(body.query, crisis, totals)
        return ExplainResponse(answer=answer)
    except GeminiDisabled:
        return ExplainResponse(
            answer="Gemini is not configured. Set GEMINI_API_KEY to enable AI reasoning."
        )
    except GeminiError as e:
        return ExplainResponse(answer=str(e))
    except Exception as e:
        return ExplainResponse(answer=f"[Fallback] Could not get explanation: {e}")
