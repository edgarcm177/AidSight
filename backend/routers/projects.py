from fastapi import APIRouter

from ..data import data_loader

router = APIRouter()

_projects_df = data_loader.load_projects()


@router.get("/")
def list_projects():
    """List projects for frontend (e.g. to pick one for Success Twin lookup)."""
    return _projects_df.to_dict(orient="records")
