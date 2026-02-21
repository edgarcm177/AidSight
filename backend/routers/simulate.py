from fastapi import APIRouter, HTTPException

from ..models import ScenarioInput, SimulationResult
from ..data import data_loader
from ..services.fragility import run_fragility_simulation

router = APIRouter()

_crises_df = data_loader.load_crises()


@router.post("/", response_model=SimulationResult)
def simulate_scenario(payload: ScenarioInput):
    if payload.crisis_id not in _crises_df["id"].values:
        raise HTTPException(status_code=404, detail="Crisis not found")

    sim = run_fragility_simulation(_crises_df, payload.model_dump())
    return sim
