from fastapi import APIRouter, HTTPException

from ..models import (
    ScenarioInput,
    SimulationResult,
    AftershockParams,
    AftershockResult,
    AffectedCountryImpact,
    TotalsImpact,
    EdgeImpact,
)
from ..data import data_loader
from ..services.fragility import run_fragility_simulation
from ..services.aftershock_data import get_aftershock_provider
from ..services.aftershock_engine import simulate_aftershock

router = APIRouter()

_crises_df = data_loader.load_crises()
_aftershock_provider = None


def _get_aftershock_provider():
    global _aftershock_provider
    if _aftershock_provider is None:
        _aftershock_provider = get_aftershock_provider()
    return _aftershock_provider


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
    """
    # Clamp inputs
    notes: list = []
    delta = payload.delta_funding_pct
    if delta < -0.3 or delta > 0.3:
        notes.append(f"delta_funding_pct clamped from {delta} to [-0.3, 0.3]")
        delta = max(-0.3, min(0.3, delta))
    horizon = max(1, min(2, payload.horizon_steps))
    cost_per = payload.cost_per_person or 250.0

    epicenter = str(payload.epicenter).upper()
    provider = _get_aftershock_provider()

    try:
        result_dict, engine_notes = simulate_aftershock(
            epicenter=epicenter,
            delta_funding_pct=delta,
            horizon_steps=horizon,
            data=provider,
            cost_per_person=cost_per,
            region_scope=payload.region_scope,
            debug=bool(payload.debug),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    notes.extend(engine_notes)

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
