from typing import Dict, Any


def build_contrarian_memo(
    crisis: Dict[str, Any],
    simulation: Dict[str, Any],
    twin: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Build a simple text memo; later you can swap in an LLM call here.
    """
    title = f"Contrarian Review: {crisis.get('name', 'Selected Crisis')}"

    lines = []

    metrics = simulation.get("metrics", {})
    baseline_ttc = metrics.get("baseline_ttc_days", 0)
    scenario_ttc = metrics.get("scenario_ttc_days", 0)

    if scenario_ttc < baseline_ttc:
        lines.append(
            f"Your scenario reduces Time to Collapse from {baseline_ttc:.0f} to "
            f"{scenario_ttc:.0f} days, increasing fragility."
        )
    else:
        lines.append(
            f"Your scenario improves Time to Collapse from {baseline_ttc:.0f} to "
            f"{scenario_ttc:.0f} days."
        )

    if twin is not None:
        lines.append(
            f"A similar project ({twin['twin_project_id']}) remained robust under shocks; "
            "consider borrowing its delivery model."
        )

    lines.append(
        "You have not yet stress-tested high inflation or fuel price shocks explicitly."
    )

    body = "\n".join(lines)
    key_risks = ["unmodeled inflation risk", "coverage deterioration", "fragility increase"]

    return {"title": title, "body": body, "key_risks": key_risks}
