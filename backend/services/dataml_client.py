"""
DataML integration: delegate to dataml.src.simulate_aftershock when available.
Fall back to backend aftershock_engine on import or runtime errors.
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_DATAML_AVAILABLE: Optional[bool] = None


def _try_import_dataml() -> bool:
    """Check if dataml.simulate_aftershock is importable and runnable."""
    global _DATAML_AVAILABLE
    if _DATAML_AVAILABLE is not None:
        return _DATAML_AVAILABLE
    try:
        from dataml.src.simulate_aftershock import simulate_aftershock as _dataml_sim
        _DATAML_AVAILABLE = True
        return True
    except Exception as e:
        logger.warning("DataML simulate_aftershock not available: %s; using backend fallback", e)
        _DATAML_AVAILABLE = False
        return False


def run_simulate_aftershock(
    country: str,
    delta_funding_pct: float,
    horizon_steps: int,
) -> Tuple[Dict[str, Any], bool]:
    """
    Run aftershock simulation. Tries DataML first; falls back to backend engine.
    Returns (result_dict, used_dataml).
    """
    if _try_import_dataml():
        try:
            from dataml.src.simulate_aftershock import simulate_aftershock as dataml_sim
            raw = dataml_sim(
                node_iso3=country,
                delta_funding_pct=delta_funding_pct,
                horizon_years=horizon_steps,
            )
            # Map DataML response to our AftershockResult schema
            affected = raw.get("affected", [])
            for a in affected:
                if "explanation" not in a:
                    a["explanation"] = "Spillover from epicenter"
            totals = {
                "total_delta_displaced": raw.get("total_extra_displaced", 0),
                "total_extra_cost_usd": raw.get("total_extra_cost_usd", 0),
                "affected_countries": len(affected),
                "max_delta_severity": max((a.get("delta_severity", 0) for a in affected), default=0.0),
            }
            result = {
                "baseline_year": raw.get("baseline_year", 2026),
                "epicenter": raw.get("epicenter", country),
                "delta_funding_pct": raw.get("delta_funding_pct", delta_funding_pct),
                "horizon_steps": horizon_steps,
                "affected": affected,
                "totals": totals,
                "graph_edges_used": None,
                "notes": raw.get("notes", []) + ["DataML simulation"],
            }
            return result, True
        except Exception as e:
            logger.warning("DataML simulate_aftershock failed: %s; falling back to backend engine", e)

    # Fallback to backend engine
    from .aftershock_data import get_aftershock_provider
    from .aftershock_engine import simulate_aftershock as backend_sim

    provider = get_aftershock_provider()
    result_dict, notes = backend_sim(
        epicenter=country,
        delta_funding_pct=delta_funding_pct,
        horizon_steps=horizon_steps,
        data=provider,
        cost_per_person=250.0,
        region_scope=None,
        debug=False,
    )
    result_dict["notes"] = notes + ["Backend fallback (DataML unavailable)"]
    return result_dict, False
