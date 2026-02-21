import logging

from fastapi import APIRouter, HTTPException

from ..models import TwinResult
from ..data import data_loader
from ..services.twins import find_success_twin

router = APIRouter()
log = logging.getLogger(__name__)

_projects_df = data_loader.load_projects()


@router.get("/{project_id}", response_model=TwinResult)
def get_success_twin_endpoint(project_id: str):
    if project_id not in _projects_df["id"].values:
        raise HTTPException(status_code=400, detail="Project not found")

    try:
        twin = find_success_twin(_projects_df, project_id)
        return twin
    except Exception as e:
        log.exception("Twins lookup failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Internal error finding Success Twin; please try again.",
        )
