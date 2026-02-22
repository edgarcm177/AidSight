"""
Build contrarian memo from crisis, simulation, and optional twin.
Uses TTC and Equity metrics for data-driven key_risks.
"""

from typing import Any, Dict, List, Optional


def _get_metrics(simulation: Any) -> Dict[str, Any]:
    """Extract metrics from SimulationResult (Pydantic) or dict."""
    if hasattr(simulation, "metrics"):
        m = simulation.metrics
        return {
            "baseline_ttc_days": m.baseline_ttc_days,
            "scenario_ttc_days": m.scenario_ttc_days,
            "baseline_equity_shift_pct": m.baseline_equity_shift_pct,
            "scenario_equity_shift_pct": m.scenario_equity_shift_pct,
        }
    return simulation.get("metrics", {})


def _get_shock_inflation(scenario: Any) -> float:
    """Get inflation_pct from ScenarioInput if available."""
    if scenario is None:
        return 0.0
    if hasattr(scenario, "shock") and hasattr(scenario.shock, "inflation_pct"):
        return float(scenario.shock.inflation_pct)
    return float(scenario.get("shock", {}).get("inflation_pct", 0.0))


def build_contrarian_memo(
    crisis: Dict[str, Any],
    simulation: Any,
    twin: Dict[str, Any] | None = None,
    scenario: Any = None,
    aftershock: Any = None,
) -> Dict[str, Any]:
    """
    Build contrarian memo with TTC, equity, and data-driven key_risks.
    Expects simulation with metrics: baseline_ttc_days, scenario_ttc_days,
    baseline_equity_shift_pct, scenario_equity_shift_pct.
    Optional scenario for inflation check; optional twin for Success Twin reference.
    """
    title = f"Contrarian Review: {crisis.get('name', 'Selected Crisis')}"

    metrics = _get_metrics(simulation)
    baseline_ttc = metrics.get("baseline_ttc_days", 0.0)
    scenario_ttc = metrics.get("scenario_ttc_days", 0.0)
    baseline_equity = metrics.get("baseline_equity_shift_pct", 0.0)
    scenario_equity = metrics.get("scenario_equity_shift_pct", 0.0)

    lines: List[str] = []

    # TTC paragraph
    if scenario_ttc < baseline_ttc - 1:
        lines.append(
            f"Time to Collapse moves from {baseline_ttc:.0f} to {scenario_ttc:.0f} days, "
            "indicating increased fragility."
        )
    elif scenario_ttc > baseline_ttc + 1:
        lines.append(
            f"Time to Collapse moves from {baseline_ttc:.0f} to {scenario_ttc:.0f} days, "
            "indicating improved resilience."
        )
    else:
        lines.append(
            f"Time to Collapse remains near {baseline_ttc:.0f} days (scenario: {scenario_ttc:.0f}), "
            "with minimal change."
        )

    # Equity paragraph
    equity_change = scenario_equity - baseline_equity
    if equity_change > 0.5:
        lines.append(
            f"Equity Shift improves by {equity_change:+.1f} percentage points, "
            "moving more funding toward high-need regions."
        )
    elif equity_change < -0.5:
        lines.append(
            f"Equity Shift worsens by {equity_change:.1f} percentage points, "
            "widening the coverage gap."
        )
    else:
        lines.append(
            f"Equity Shift changes by {equity_change:+.1f} percentage points, "
            "with minimal impact."
        )

    # Aftershock spillover paragraph (if provided)
    if aftershock is not None:
        aft = aftershock if isinstance(aftershock, dict) else getattr(aftershock, "model_dump", lambda: {})()
        ep = aft.get("epicenter", "unknown")
        tot = aft.get("totals", {})
        disp = tot.get("total_delta_displaced", 0)
        cost = tot.get("total_extra_cost_usd", 0)
        n = tot.get("affected_countries", 0)
        lines.append(
            f"Spillover impact from epicenter {ep}: {n} affected countries, "
            f"~{disp:,.0f} additional displaced, ~${cost:,.0f} extra cost estimated."
        )

    # Twin paragraph
    if twin is not None:
        twin_dict = twin if isinstance(twin, dict) else getattr(twin, "model_dump", lambda: {})()
        twin_id = twin_dict.get("twin_project_id", "unknown")
        lines.append(
            f"A comparable project (ID {twin_id}) remained stable under similar conditions; "
            "consider adopting its delivery model."
        )

    body = "\n".join(lines)

    # Data-driven key_risks
    key_risks: List[str] = []
    if scenario_ttc < baseline_ttc - 1:
        key_risks.append("fragility_increase")
    if scenario_equity < 0:
        key_risks.append("equity_regression")
    inflation_pct = _get_shock_inflation(scenario)
    if inflation_pct != 0:
        key_risks.append("inflation_risk")
    if not key_risks:
        key_risks.append("model_uncertainty")

    return {"title": title, "body": body, "key_risks": key_risks}
