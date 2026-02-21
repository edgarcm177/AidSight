from fastapi import APIRouter
from typing import List

from ..models import Crisis
from ..data import data_loader

router = APIRouter()

_crises_df = data_loader.load_crises()


@router.get("/", response_model=List[Crisis])
def list_crises():
    return _crises_df.to_dict(orient="records")


@router.get("/{crisis_id}", response_model=Crisis)
def get_crisis(crisis_id: str):
    row = _crises_df.loc[_crises_df["id"] == crisis_id].iloc[0]
    return row.to_dict()
