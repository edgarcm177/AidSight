from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import crises, simulate, twins, memos

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


@app.get("/")
def root():
    return {"status": "ok", "app": "AidSight Strategy Sandbox"}
