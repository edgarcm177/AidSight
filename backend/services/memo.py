"""
Build contrarian memo from crisis, simulation, optional twin, and optional aftershock.
Uses TTC and Equity metrics for fragility; uses Aftershock metrics for spillover.
Aftershock can stand alone when simulation is a placeholder (all-zero TTC/equity).
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


def _is_placeholder_simulation(metrics: Dict[str, Any]) -> bool:
    """
    Detect a placeholder/empty simulation: TTC and equity metrics all zero or missing.
    Used when the frontend sends minimal placeholders for aftershock-only flow.
    Aftershock is intended to augment TTC/equity, but can stand alone when this is the only signal.
    """
    baseline_ttc = metrics.get("baseline_ttc_days", 0.0)
    scenario_ttc = metrics.get("scenario_ttc_days", 0.0)
    baseline_equity = metrics.get("baseline_equity_shift_pct", 0.0)
    scenario_equity = metrics.get("scenario_equity_shift_pct", 0.0)
    return (
        baseline_ttc == 0.0
        and scenario_ttc == 0.0
        and baseline_equity == 0.0
        and scenario_equity == 0.0
    )


def _format_compact_num(n: float) -> str:
    """Format numbers compactly: 112000 → 110k, 1500000 → 1.5M."""
    n = max(0, float(n))
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return f"{int(n)}"


def _format_compact_cost(c: float) -> str:
    """Format USD compactly: 24000000 → $24M."""
    c = max(0, float(c))
    if c >= 1_000_000:
        val = c / 1_000_000
        return f"${val:.1f}M" if val < 10 else f"${int(val)}M"
    if c >= 1_000:
        return f"${c / 1_000:.0f}k"
    return f"${int(c)}"


def _build_aftershock_spillover_paragraph(aftershock: Any) -> str:
    """Build a tight, UN-judge-ready spillover narrative from aftershock result."""
    aft = aftershock if isinstance(aftershock, dict) else getattr(aftershock, "model_dump", lambda: {})()
    ep = aft.get("epicenter", "unknown")
    delta_pct = float(aft.get("delta_funding_pct", 0))
    horizon = int(aft.get("horizon_steps", 2))
    tot = aft.get("totals", {})
    disp = tot.get("total_delta_displaced", 0)
    cost = tot.get("total_extra_cost_usd", 0)
    affected = aft.get("affected", [])
    top_affected = sorted(
        (a for a in affected if isinstance(a, dict) and "delta_displaced" in a),
        key=lambda a: float(a.get("delta_displaced", 0)),
        reverse=True,
    )[:3]
    country_names = [a.get("country", "?") for a in top_affected if a.get("country")]
    disp_str = _format_compact_num(disp)
    cost_str = _format_compact_cost(cost)
    if delta_pct < 0:
        pct_str = f"{abs(delta_pct * 100):.0f}%"
        funding_phrase = f"Cutting funding by {pct_str} in {ep}"
    elif delta_pct > 0:
        pct_str = f"{delta_pct * 100:.0f}%"
        funding_phrase = f"Increasing funding by {pct_str} in {ep}"
    else:
        funding_phrase = f"Funding changes in {ep}"
    country_phrase = " and ".join(country_names[:2]) if len(country_names) >= 2 else (country_names[0] if country_names else "neighboring countries")
    line = (
        f"Spillover risk: {funding_phrase} leads to ~{disp_str} additional displaced people, "
        f"mostly in {country_phrase}, and raises future response costs by ~{cost_str} over the next {horizon} year{'s' if horizon != 1 else ''}."
    )
    return line


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

    # Detect placeholder simulation (all-zero TTC/equity) for aftershock-only flow.
    is_placeholder = _is_placeholder_simulation(metrics)
    has_aftershock = aftershock is not None

    lines: List[str] = []

    # When aftershock is the main focus and simulation is placeholder, prioritize spillover.
    # Otherwise, TTC and equity paragraphs remain; aftershock adds a spillover paragraph.
    if has_aftershock and is_placeholder:
        # Aftershock-only: lead with labeled spillover paragraph; omit TTC/equity (all zeros).
        lines.append(_build_aftershock_spillover_paragraph(aftershock))
    else:
        # Real TTC/equity and/or no aftershock: keep standard paragraphs.
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

    # Spillover risk paragraph: when we have both real TTC/equity and aftershock, add labeled spillover.
    # (When aftershock-only, spillover is already the lead paragraph above.)
    if has_aftershock and not is_placeholder:
        lines.append(_build_aftershock_spillover_paragraph(aftershock))

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
    if has_aftershock:
        key_risks.append("spillover_risk")
    if not key_risks:
        key_risks.append("model_uncertainty")

    return {"title": title, "body": body, "key_risks": key_risks}
