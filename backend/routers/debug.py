# Debug-only status endpoint (safe for hackathon demos, not production-ready auth)

from fastapi import APIRouter

from ..data import data_loader
from ..services.data_status import get_crisis_data_status

router = APIRouter()


@router.get("/data-status")
def data_status():
    """Return crisis data health: row_count, null_rates, imputation_rates."""
    crises_df = data_loader.load_crises()
    return get_crisis_data_status(crises_df)
