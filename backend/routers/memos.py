from fastapi import APIRouter, HTTPException

from ..models import MemoRequest, MemoResponse
from ..data import data_loader
from ..services.memo import build_contrarian_memo

router = APIRouter()

_crises_df = data_loader.load_crises()


@router.post("/", response_model=MemoResponse)
def generate_memo(payload: MemoRequest):
    if payload.crisis_id is None or payload.simulation is None:
        raise HTTPException(status_code=400, detail="crisis_id and simulation required for now")

    crisis_row = _crises_df.loc[_crises_df["id"] == payload.crisis_id].iloc[0]
    crisis_dict = crisis_row.to_dict()

    memo_dict = build_contrarian_memo(
        crisis_dict, payload.simulation, payload.twin, payload.scenario, payload.aftershock
    )
    return memo_dict
