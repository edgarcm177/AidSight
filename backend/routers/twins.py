from fastapi import APIRouter, HTTPException

from ..models import TwinResult
from ..data import data_loader
from ..services.twins import find_success_twin

router = APIRouter()

_projects_df = data_loader.load_projects()


@router.get("/{project_id}", response_model=TwinResult)
def get_success_twin(project_id: str):
    if project_id not in _projects_df["id"].values:
        raise HTTPException(status_code=404, detail="Project not found")

    twin = find_success_twin(_projects_df, project_id)
    return twin
