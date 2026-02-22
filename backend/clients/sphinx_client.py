"""
Sphinx prompt for crisis + aftershock explanation.
Used by the explain flow (e.g. Gemini client) to build the LLM prompt.
"""

SPHINX_PROMPT_TEMPLATE = """You are Sphinx, an AI analyst explaining humanitarian crises to UN planners.

The user sees a "Spillover Metrics" panel with exactly these values. Use the SAME numbers in your explanation:
- Severity: {severity_score} / 10
- Funding coverage: {coverage_pct}% funded
- Underfunded status: {underfunded_status}
- This scenario adds: {delta_displaced} extra displaced people, {delta_cost_usd} USD extra response cost

How these are produced (use this rationale in your explanation):
- Severity is on a comparable 0–10 scale (normalized across crises). The simulation propagates stress over the time horizon: longer horizon means more spillover, so severity can worsen in the epicenter and surrounding areas over time.
- Coverage is the share of assessed need that is funded (funding_received / funding_required). Funding change is applied with diminishing returns (each extra % of funding has a smaller effect). Time horizon adds a drift: if underfunded (<50%), coverage tends to worsen over time; if well-funded, the situation can settle (coverage drifts up).
- Status is derived from coverage only: <50% Underfunded vs peers, 50–99% Adequately funded, ≥100% Overfunded.

Your job: explain what these numbers mean in context and WHY this crisis is risky or overlooked. Weave in the rationale above (time horizon, settling vs worsening, diminishing returns) where relevant. Use the exact values the user sees; then explain cause and effect and why planners should care.

User question: "{query}"

Answer in 3–5 short sentences. Use the exact values and the rationale above."""


def build_sphinx_prompt(query: str, crisis: dict, aftershock_totals: dict) -> str:
    """Fill the Sphinx prompt template. Uses same values as the Spillover impact panel."""
    crisis = crisis or {}
    at = aftershock_totals or {}
    severity = crisis.get("severity_score", "—")
    if isinstance(severity, (int, float)):
        severity = f"{float(severity) * 10:.1f}" if severity is not None else "—"
    return SPHINX_PROMPT_TEMPLATE.format(
        country=crisis.get("country", "—"),
        year=crisis.get("year", "—"),
        severity_score=severity,
        coverage_pct=crisis.get("coverage_pct", "—"),
        underfunded_status=crisis.get("underfunded_status", "—"),
        delta_displaced=at.get("total_delta_displaced", at.get("delta_displaced", "—")),
        delta_cost_usd=at.get("total_extra_cost_usd", at.get("delta_cost_usd", "—")),
        query=query or "Explain what these numbers mean in context and why this crisis is risky or overlooked.",
    )
