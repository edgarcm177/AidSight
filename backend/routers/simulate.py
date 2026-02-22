from fastapi import APIRouter, HTTPException

from ..models import (
    ScenarioInput,
    SimulationResult,
    SimulateRequest,
    SimulateResponse,
    AftershockParams,
    AftershockResult,
    AffectedCountryImpact,
    TotalsImpact,
    EdgeImpact,
    EpicenterNeighborsResponse,
    NeighborSituation,
)
from ..data import data_loader
from ..services.fragility import run_fragility_simulation
from ..services.dataml_client import run_simulate_aftershock
from ..services.aftershock_data import get_aftershock_provider

router = APIRouter()

_crises_df = data_loader.load_crises()


@router.post("/shock", response_model=SimulateResponse)
def simulate_shock(request: SimulateRequest):
    """
    Aftershock simulation via DataML. Direct pass-through to simulate_aftershock.
    Matches DataML contract: node_iso3, delta_funding_pct, horizon_years.
    """
    try:
        from dataml.src.simulate_aftershock import simulate_aftershock

        out = simulate_aftershock(
            node_iso3=request.country.upper(),
            delta_funding_pct=request.delta_funding_pct,
            horizon_years=request.horizon_steps,
        )
        return SimulateResponse.model_validate(out)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DataML simulate_aftershock failed: {e}")


def _criticality(severity: float, coverage_proxy: float) -> float:
    """Single 0-1 scale from severity and coverage (high = worse). Same for epicenter and neighbors."""
    return max(0.0, min(1.0, (severity + (1.0 - coverage_proxy)) / 2.0))


@router.get("/neighbors", response_model=EpicenterNeighborsResponse)
def get_epicenter_neighbors(epicenter: str):
    """
    Return 1-hop graph neighbors and epicenter baseline with continuous criticality (0-1)
    so map can use one spectrum: green (low) → yellow → orange → red (high).
    """
    iso = str(epicenter).strip().upper()
    if not iso:
        raise HTTPException(status_code=400, detail="epicenter is required")
    provider = get_aftershock_provider()
    edges = provider.get_edges()
    neighbor_isos = set()
    for e in edges:
        src = str(e.get("src", "")).upper()
        dst = str(e.get("dst", "")).upper()
        if src == iso:
            neighbor_isos.add(dst)
        if dst == iso:
            neighbor_isos.add(src)
    year = provider.get_baseline_year()
    panel = provider.get_country_panel(year)
    ep_row = panel.get(iso) or {}
    ep_severity = float(ep_row.get("severity", 0.5))
    ep_coverage = float(ep_row.get("coverage_proxy", ep_row.get("coverage", 0.5)))
    epicenter_criticality = _criticality(ep_severity, ep_coverage)
    result = []
    for country_iso in sorted(neighbor_isos):
        row = panel.get(country_iso) or {}
        severity = float(row.get("severity", 0.5))
        coverage_proxy = float(row.get("coverage_proxy", row.get("coverage", 0.5)))
        result.append(
            NeighborSituation(
                country=country_iso,
                severity=severity,
                coverage_proxy=coverage_proxy,
                criticality=_criticality(severity, coverage_proxy),
            )
        )
    return EpicenterNeighborsResponse(
        epicenter=iso,
        epicenter_criticality=epicenter_criticality,
        neighbors=result,
    )


@router.post("/", response_model=SimulationResult)
def simulate_scenario(payload: ScenarioInput):
    if payload.crisis_id not in _crises_df["id"].values:
        raise HTTPException(status_code=404, detail="Crisis not found")

    sim = run_fragility_simulation(_crises_df, payload.model_dump())
    return sim


@router.post("/aftershock", response_model=AftershockResult)
def simulate_aftershock_route(payload: AftershockParams):
    """
    Aftershock spillover simulation: epicenter funding change propagates to neighbors.
    Delegates to DataML simulate_aftershock when available; falls back to backend engine.
    """
    notes: list = []
    delta = payload.delta_funding_pct
    if delta < -0.3 or delta > 0.3:
        notes.append(f"delta_funding_pct clamped from {payload.delta_funding_pct} to [-0.3, 0.3]")
        delta = max(-0.3, min(0.3, delta))
    horizon = max(1, min(2, payload.horizon_steps))
    epicenter = str(payload.epicenter).upper()

    try:
        result_dict, _used_dataml = run_simulate_aftershock(
            country=epicenter,
            delta_funding_pct=delta,
            horizon_steps=horizon,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    notes.extend(result_dict.get("notes", []))

    # Normalize affected so map can show post-aftershock spectrum: include epicenter and set projected_* for every entry
    provider = get_aftershock_provider()
    year = result_dict.get("baseline_year", provider.get_baseline_year())
    panel = provider.get_country_panel(year)
    affected_raw = result_dict["affected"]
    affected_isos = {a.get("country") for a in affected_raw if a.get("country")}
    if epicenter and epicenter not in affected_isos:
        row = panel.get(epicenter) or {}
        base_sev = float(row.get("severity", 0.5))
        base_cov = float(row.get("coverage_proxy", row.get("coverage", 0.5)))
        proj_cov = max(0.0, min(3.0, base_cov + delta))
        affected_raw.insert(0, {
            "country": epicenter,
            "delta_severity": 0.0,
            "delta_displaced": 0.0,
            "extra_cost_usd": 0.0,
            "prob_underfunded_next": max(0.0, min(1.0, 1.0 - proj_cov)),
            "projected_severity": base_sev,
            "projected_coverage": proj_cov,
        })
    for a in affected_raw:
        country_iso = (a.get("country") or "").upper()
        if not country_iso:
            continue
        row = panel.get(country_iso) or {}
        base_sev = float(row.get("severity", 0.5))
        base_cov = float(row.get("coverage_proxy", row.get("coverage", 0.5)))
        ds = float(a.get("delta_severity", 0.0))
        if "projected_severity" not in a or a["projected_severity"] is None:
            proj_sev = base_sev + ds
            if delta > 0:
                proj_sev = min(proj_sev, base_sev)
            a["projected_severity"] = round(max(0.0, proj_sev), 4)
        if "projected_coverage" not in a or a["projected_coverage"] is None:
            proj_cov = base_cov + (delta if country_iso == epicenter else 0.0)
            a["projected_coverage"] = round(max(0.0, min(3.0, proj_cov)), 4)

    affected = [AffectedCountryImpact(**a) for a in affected_raw]
    totals = TotalsImpact(**result_dict["totals"])
    edges_used = None
    if result_dict.get("graph_edges_used"):
        edges_used = [EdgeImpact(**e) for e in result_dict["graph_edges_used"]]

    return AftershockResult(
        baseline_year=result_dict["baseline_year"],
        epicenter=result_dict["epicenter"],
        delta_funding_pct=result_dict["delta_funding_pct"],
        horizon_steps=result_dict["horizon_steps"],
        affected=affected,
        totals=totals,
        graph_edges_used=edges_used,
        notes=notes,
    )
