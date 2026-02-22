"""
Gemini LLM client for Sphinx-style crisis explanation.
Uses GEMINI_API_KEY, GEMINI_API_BASE, GEMINI_MODEL.
Uses Google's native generateContent API (generativelanguage.googleapis.com).
"""

import logging
import os
import time

import requests

from .sphinx_client import build_sphinx_prompt

GeminiDisabled = type("GeminiDisabled", (Exception,), {})
GeminiError = type("GeminiError", (Exception,), {})

logger = logging.getLogger(__name__)

# Native Gemini API (works with GEMINI_API_KEY from Google AI)
DEFAULT_GEMINI_API_BASE = "https://generativelanguage.googleapis.com"

# Fallback models when primary hits 429 (each model has its own quota)
# Use model names that exist in Gemini API; 1.5 names can 404 on v1beta
DEFAULT_FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]


def _parse_model_list(env_value: str, primary: str) -> list[str]:
    """Primary first, then comma-separated fallbacks from env (if any)."""
    out = [primary]
    if env_value:
        for m in env_value.split(","):
            m = m.strip()
            if m and m != primary:
                out.append(m)
    else:
        for m in DEFAULT_FALLBACK_MODELS:
            if m != primary:
                out.append(m)
    return out


def explain_crisis_via_gemini(
    query: str, crisis: dict, aftershock_totals: dict
) -> str:
    """Call Gemini generateContent with Sphinx prompt. On 429, tries fallback models."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    api_base = (
        os.environ.get("GEMINI_API_BASE", "").strip().rstrip("/")
        or DEFAULT_GEMINI_API_BASE
    )
    primary_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    fallbacks_env = os.environ.get("GEMINI_FALLBACK_MODELS", "").strip()
    models_to_try = _parse_model_list(fallbacks_env, primary_model)

    if not api_key:
        raise GeminiDisabled("GEMINI_API_KEY must be set")

    prompt = build_sphinx_prompt(query, crisis, aftershock_totals)
    payload = {
        "systemInstruction": {
            "parts": [{"text": "You are Sphinx, an AI analyst for humanitarian planners."}]
        },
        "contents": [{"parts": [{"text": prompt}]}],
    }
    headers = {"Content-Type": "application/json"}
    rate_limit_msg = "Gemini rate limit reached. Please wait a minute and try again."

    def do_request(model_name: str):
        model_path = model_name if model_name.startswith("models/") else f"models/{model_name}"
        path = f"/v1beta/{model_path}:generateContent"
        url = f"{api_base}{path}?key={api_key}"
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 429:
            return None, rate_limit_msg
        if resp.status_code == 404:
            return None, f"Model {model_name} not found"
        resp.raise_for_status()
        return resp.json(), None

    data = None
    err = rate_limit_msg
    for i, model in enumerate(models_to_try):
        if i > 0:
            time.sleep(2)  # brief delay before switching model
        data, err = do_request(model)
        if err is None:
            logger.info("Gemini succeeded with model=%s", model)
            break
        logger.warning("Gemini failed on model=%s: %s, trying next", model, err)

    try:
        if err is not None:
            raise GeminiError(err)
        candidates = data.get("candidates")
        if not candidates:
            raise GeminiError("Gemini response had no candidates")
        parts = candidates[0].get("content", {}).get("parts")
        if not parts or "text" not in parts[0]:
            raise GeminiError("Gemini response missing text in candidate")
        return parts[0]["text"].strip()
    except GeminiError:
        raise
    except requests.RequestException as e:
        if getattr(e, "response", None) and getattr(e.response, "status_code", None) == 429:
            raise GeminiError(rate_limit_msg) from e
        logger.warning("Gemini request failed: %s", e)
        raise GeminiError(f"Gemini request failed: {e}") from e
    except (KeyError, IndexError) as e:
        logger.warning("Gemini response malformed: %s", e)
        raise GeminiError("Gemini response missing expected fields") from e
