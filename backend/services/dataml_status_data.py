"""
DataML status data: load nodes.json, edges.json, baseline_predictions.json for GET /status.
Fall back to backend aftershock_data when DataML files are missing.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# dataml/data/processed/ relative to repo root (parent of backend)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATAML_PROCESSED = REPO_ROOT / "dataml" / "data" / "processed"
NODES_JSON = DATAML_PROCESSED / "nodes.json"
EDGES_JSON = DATAML_PROCESSED / "edges.json"
BASELINE_JSON = DATAML_PROCESSED / "baseline_predictions.json"


def load_status_from_dataml() -> Optional[Tuple[int, List[Dict[str, Any]], List[Dict[str, Any]], List[int], List[str]]]:
    """
    Load baseline year, countries, edges, years, notes from DataML.
    Returns (baseline_year, countries, edges, available_years, notes) or None if files missing.
    """
    if not NODES_JSON.exists() or not EDGES_JSON.exists():
        return None

    try:
        with open(NODES_JSON) as f:
            nodes_raw = json.load(f)
        with open(EDGES_JSON) as f:
            edges_raw = json.load(f)
        baseline_raw: List[Dict[str, Any]] = []
        if BASELINE_JSON.exists():
            with open(BASELINE_JSON) as f:
                baseline_raw = json.load(f)
    except Exception as e:
        logger.warning("Failed to load DataML status files: %s", e)
        return None

    # Build baseline_pred map: country -> {severity_pred_baseline, displacement_in_pred_baseline}
    baseline_map: Dict[str, Dict[str, Any]] = {}
    baseline_year = 2026
    for row in baseline_raw:
        c = row.get("country", "")
        baseline_map[c] = row
        baseline_year = row.get("baseline_year", 2026)

    countries: List[Dict[str, Any]] = []
    for row in nodes_raw:
        iso3 = str(row.get("country", "")).upper()
        pred = baseline_map.get(iso3, {})
        severity = row.get("severity", pred.get("severity_pred_baseline", 0.5))
        funding = row.get("funding_total_usd", row.get("funding_usd", 0))
        disp_in = pred.get("displacement_in_pred_baseline", row.get("beneficiaries_total", 0))
        disp_out = 0  # nodes.json may not have displaced_out
        underfund = row.get("underfunding_score", 0.5)
        risk_score = float(severity) * float(underfund)
        countries.append({
            "country": iso3,
            "severity": round(float(severity), 4),
            "funding_usd": float(funding),
            "displaced_in": float(disp_in),
            "displaced_out": float(disp_out),
            "risk_score": round(float(risk_score), 4),
        })

    edges: List[Dict[str, Any]] = []
    for e in edges_raw:
        src = str(e.get("source_country", e.get("src", ""))).upper()
        dst = str(e.get("target_country", e.get("dst", ""))).upper()
        w = float(e.get("weight", 1.0))
        edges.append({"src": src, "dst": dst, "weight": w})

    notes = ["DataML: nodes.json, edges.json, baseline_predictions.json"]
    return (baseline_year, countries, edges, [baseline_year], notes)


def get_status_data() -> Tuple[int, List[Dict[str, Any]], List[Dict[str, Any]], List[int], List[str]]:
    """
    Get status data. Uses DataML if available; else backend aftershock provider.
    Returns (baseline_year, countries, edges, available_years, notes).
    """
    dataml_result = load_status_from_dataml()
    if dataml_result is not None:
        return dataml_result

    from .aftershock_data import get_aftershock_provider
    provider = get_aftershock_provider()
    year = provider.get_baseline_year()
    panel = provider.get_country_panel(year)
    edges_raw = provider.get_edges()
    years = provider.get_available_years()

    countries = []
    for iso3, row in panel.items():
        sev = row.get("severity", 0.5)
        cov = row.get("coverage_proxy", 0.5)
        risk_score = (1 - cov) * sev
        countries.append({
            "country": iso3,
            "severity": round(sev, 4),
            "funding_usd": float(row.get("funding_usd", 0)),
            "displaced_in": float(row.get("displaced_in", 0)),
            "displaced_out": float(row.get("displaced_out", 0)),
            "risk_score": round(risk_score, 4),
        })

    edges = [
        {"src": str(e.get("src", "")), "dst": str(e.get("dst", "")), "weight": float(e.get("weight", 0))}
        for e in edges_raw
    ]

    notes = getattr(provider, "_notes", []) if hasattr(provider, "_notes") else []
    notes.append("Backend fallback (DataML files not found)")
    return (year, countries, edges, years, notes)
