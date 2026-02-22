"""
Sphinx reasoning client for crisis explanation.
Enabled if and only if SPHINX_BASE_URL is set (no API key required).
Posts query + context JSON; expects {answer} or similar in response.
Raises SphinxDisabled when URL missing or HTTP call fails.
"""

import json
import logging
import os

SphinxDisabled = type("SphinxDisabled", (Exception,), {})

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    """Sphinx is enabled when SPHINX_BASE_URL is set (no API key required)."""
    url = os.environ.get("SPHINX_BASE_URL", "").strip()
    return bool(url)


def explain_crisis(crisis_id: str, metrics: dict, aftershock: dict | None) -> str:
    """
    POST to SPHINX_BASE_URL with query + context.
    Returns 2–3 sentence explanation. Raises SphinxDisabled on failure.
    """
    if not _is_configured():
        raise SphinxDisabled("SPHINX_BASE_URL not set")

    url = os.environ["SPHINX_BASE_URL"].strip().rstrip("/")

    payload = {
        "query": (
            f"Explain why crisis {crisis_id} appears overlooked compared to similar crises, "
            f"using severity, funding, underfunding_score, pooled_fund_coverage, and any "
            f"aftershock spillover metrics if provided."
        ),
        "context": {
            "crisis": metrics,
            "aftershock_totals": aftershock or None,
        },
    }

    headers = {"Content-Type": "application/json"}
    if os.environ.get("SPHINX_API_KEY", "").strip():
        headers["Authorization"] = f"Bearer {os.environ['SPHINX_API_KEY'].strip()}"

    try:
        import requests

        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code != 200:
            logger.warning("Sphinx API %s: %s", r.status_code, r.text[:200])
            raise SphinxDisabled(f"Sphinx API error: {r.status_code}")

        data = r.json()
        # Sphinx may return {"answer": "..."} or {"explanation": "..."} or {"text": "..."}
        text = (
            data.get("answer")
            or data.get("explanation")
            or data.get("text")
            or data.get("response")
        )
        if isinstance(text, str):
            return text.strip()
        raise SphinxDisabled("Sphinx response missing answer/explanation field")
    except SphinxDisabled:
        raise
    except Exception as e:
        logger.warning("Sphinx request failed: %s", e)
        raise SphinxDisabled(f"Sphinx request failed: {e}") from e
