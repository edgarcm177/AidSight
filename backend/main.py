from pathlib import Path

from dotenv import load_dotenv

env_file = Path(__file__).resolve().parents[1] / ".env.local"
if env_file.exists():
    load_dotenv(env_file, override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import crises, memos, simulate, twins, status, project_benchmarking, projects, vectorai_routes, explain, debug

app = FastAPI(title="AidSight Strategy Sandbox")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(crises.router, prefix="/crises", tags=["crises"])
app.include_router(simulate.router, prefix="/simulate", tags=["simulate"])
app.include_router(twins.router, prefix="/twins", tags=["twins"])
app.include_router(memos.router, prefix="/memos", tags=["memos"])
app.include_router(status.router, prefix="/status", tags=["status"])
app.include_router(project_benchmarking.router, tags=["project_benchmarking"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(vectorai_routes.router, tags=["vectorai"])
app.include_router(explain.router, prefix="/explain", tags=["explain"])
app.include_router(debug.router, prefix="/debug", tags=["debug"])


@app.get("/")
def root():
    return {"status": "ok", "app": "AidSight Strategy Sandbox"}
