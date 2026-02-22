from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import crises, memos, simulate, twins, status, project_benchmarking

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


@app.get("/")
def root():
    return {"status": "ok", "app": "AidSight Strategy Sandbox"}
