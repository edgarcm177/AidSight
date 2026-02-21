"""AidSight FastAPI backend."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import MemoContext, ScenarioParams
from services.data_provider import DataProvider, MockDataProvider
from services.memo_service import get_memo_client
from services.scenario_engine import run_stress_test
from services.vector_service import get_vector_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AidSight API",
    description="Portfolio stress-testing terminal for humanitarian funding",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path(os.getenv("DATA_PATH", Path(__file__).parent / "mock_data"))
data_provider: DataProvider = MockDataProvider(DATA_PATH)


@app.get("/health")
def health():
    return {"status": "ok", "app": "AidSight"}


@app.get("/regions")
def list_regions(scenario_preset: str | None = None):
    """List regions. Optional scenario_preset applies a preset stress (e.g. 'moderate', 'severe')."""
    regions = data_provider.get_regions()
    if scenario_preset == "moderate":
        params = ScenarioParams(
            inflation_shock=0.1,
            climate_shock=0.05,
            access_shock=0.1,
            funding_delta=0,
        )
        result = run_stress_test(regions, params)
        return [m.model_dump() for m in result.updated_region_metrics]
    if scenario_preset == "severe":
        params = ScenarioParams(
            inflation_shock=0.2,
            climate_shock=0.15,
            access_shock=0.2,
            funding_delta=0,
        )
        result = run_stress_test(regions, params)
        return [m.model_dump() for m in result.updated_region_metrics]
    return [r.model_dump() for r in regions]


@app.get("/regions/{region_id}")
def get_region(region_id: str):
    region = data_provider.get_region(region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    projects = data_provider.get_projects(region_id=region_id)
    return {
        "region": region.model_dump(),
        "projects": [p.model_dump() for p in projects],
    }


@app.post("/scenario/run")
def run_scenario(params: ScenarioParams):
    regions = data_provider.get_regions()
    result = run_stress_test(regions, params)
    return {
        "updated_region_metrics": [m.model_dump() for m in result.updated_region_metrics],
        "top_downside_regions": result.top_downside_regions,
        "suggested_allocations": [a.model_dump() for a in result.suggested_allocations],
        "regret_score": result.regret_score,
    }


@app.get("/projects")
def list_projects(region_id: str | None = None, flagged: bool | None = None):
    projects = data_provider.get_projects(region_id=region_id, flagged=flagged)
    return [p.model_dump() for p in projects]


@app.get("/projects/{project_id}")
def get_project(project_id: str):
    project = data_provider.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.model_dump()


@app.post("/projects/{project_id}/comparables")
def get_comparables(project_id: str, top_k: int = 5):
    project = data_provider.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    projects = data_provider.get_projects()
    vector_svc = get_vector_service(projects)
    text = f"{project.title} {project.description} {project.sector}"
    comparables = vector_svc.query_similar(text, top_k=top_k)
    return [c.model_dump() for c in comparables]


@app.post("/memo/generate")
def generate_memo(context: MemoContext):
    client = get_memo_client()
    memo = client.generate_memo(context)
    return memo.model_dump()
