import logging

from fastapi import APIRouter, HTTPException

from ..models import MemoRequest, MemoResponse
from ..data import data_loader
from ..services.memo import build_contrarian_memo

router = APIRouter()
log = logging.getLogger(__name__)

_crises_df = data_loader.load_crises()


@router.post("/", response_model=MemoResponse)
def generate_memo(payload: MemoRequest):
    if payload.crisis_id is None or payload.simulation is None:
        raise HTTPException(status_code=400, detail="crisis_id and simulation required")

    if payload.crisis_id not in _crises_df["id"].values:
        raise HTTPException(status_code=400, detail="Crisis not found")

    try:
        crisis_row = _crises_df.loc[_crises_df["id"] == payload.crisis_id].iloc[0]
        crisis_dict = crisis_row.to_dict()

        memo_dict = build_contrarian_memo(
            crisis_dict, payload.simulation, payload.twin, payload.scenario
        )
        return memo_dict
    except Exception as e:
        log.exception("Memo generation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Internal error generating memo; please try again.",
        )
