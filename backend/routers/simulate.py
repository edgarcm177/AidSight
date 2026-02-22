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
)
from ..data import data_loader
from ..services.fragility import run_fragility_simulation
from ..services.dataml_client import run_simulate_aftershock

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

    affected = [AffectedCountryImpact(**a) for a in result_dict["affected"]]
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
