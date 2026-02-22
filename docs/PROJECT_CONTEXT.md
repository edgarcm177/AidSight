# Ripplect – Project Context

*This doc captures project structure, tech choices, implementation status, and open work. Use it to restore context after a session reset.*

---

## Project Overview

**Ripplect** is a portfolio stress-testing / spillover simulation tool for humanitarian funding. Core flow:

1. User selects epicenter country from heatmap
2. User adjusts funding slider (`delta_funding_pct`)
3. Backend runs spillover simulation (graph propagation)
4. UI shows shockwave and affected neighbors + totals

**Comparable Trades** (Actian) and **Memo** (Sphinx) are secondary features.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Pydantic v2 |
| Data | Pandas, Parquet; mock JSON for aftershock |
| ML (Twins) | sentence-transformers (all-MiniLM-L6-v2), scikit-learn cosine similarity |
| Frontend | Vite + React (in `frontend/`); Streamlit (in `frontend/app.py`) |
| Maps | (Frontend) Leaflet + OpenStreetMap; GeoJSON in `geo/` |

---

## Repo Structure

```
Ripplect/
├── backend/                 # FastAPI app
│   ├── main.py              # App entry; routers: crises, simulate, twins, memos, status
│   ├── models.py            # Pydantic models (Crisis, ScenarioInput, AftershockParams, etc.)
│   ├── data/                # Data package (data_loader)
│   ├── routers/             # crises, simulate, twins, memos, status
│   ├── services/            # fragility, memo, twins, scenarios, aftershock_engine, aftershock_data
│   ├── mock_data/           # aftershock_panel.json, aftershock_graph.json
│   ├── docs/                # AFTERSHOCK.md
│   └── tests/               # test_aftershock.py, test_scenario.py
├── frontend/                # Vite + React (main UI)
├── apps/                    # (May exist) Next.js/web, api – from earlier scaffold
├── geo/                     # GeoJSON placeholders
├── docs/                    # PROJECT_CONTEXT.md, etc.
├── RUN.md                   # How to run app
└── docker-compose.yml       # (If present) api + web
```

---

## Backend – Implemented

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Root health |
| GET | `/crises/` | List crises |
| GET | `/crises/{id}` | Get crisis |
| POST | `/simulate/` | Fragility sim (crisis + funding changes + shock) |
| **POST** | **`/simulate/aftershock`** | **Aftershock spillover sim** (epicenter, delta_funding_pct) |
| GET | `/twins/{project_id}` | Success Twin (similar project via sentence-transformers) |
| POST | `/memos/` | Generate contrarian memo (crisis + sim + twin; optional aftershock) |
| **GET** | **`/status/`** | **Baseline status** (countries, edges, years) for map |

### Key Services

- **aftershock_engine.py**: Graph propagation; alpha/beta/decay; stress → severity + displaced
- **aftershock_data.py**: `AftershockDataProvider`; `MockAftershockDataProvider`; `FileAftershockDataProvider` (falls back to mock if `data/processed/region_panel.parquet` and `models/graph.json` missing)
- **twins.py**: sentence-transformers + sklearn cosine; in-process, **not Actian**
- **memo.py**: Rule-based `build_contrarian_memo`; **not Sphinx**; accepts optional `aftershock` for spillover paragraph

### Data

- **Crises/Projects**: `backend/data/` or `backend/services/data_loader.py` loads `crises.parquet`, `projects.parquet` from `DATA_DIR`
- **Aftershock**: `backend/mock_data/aftershock_panel.json`, `aftershock_graph.json` (6 countries, 10 edges)

### How to Run Backend

From **project root** (required for package imports):

```bash
cd Ripplect
pip install -r backend/requirements.txt   # once
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API: http://localhost:8000 | Docs: http://localhost:8000/docs

---

## Backend – Not Implemented / Gaps

| Item | Status | Notes |
|------|--------|------|
| Actian VectorAI | Not implemented | Twins use in-process sentence-transformers + sklearn |
| Sphinx AI | Not implemented | Memo is rule-based |
| Real data pipeline | Mock only | `region_panel.parquet` + `graph.json` can be dropped in; `FileAftershockDataProvider` picks them up |
| GET /projects, GET /projects/{id} | Not present | Only `/twins/{project_id}` for similar projects |
| POST /scenario/run (regions) | Not present | Only crisis-based `/simulate/` and `/simulate/aftershock` |
| Docker Compose | May not exist | Check root for docker-compose.yml |

---

## Frontend

- **Vite/React** in `frontend/`: `npm install` + `npm run dev`; uses `NEXT_PUBLIC_API_URL` or `VITE_API_BASE_URL` (default http://localhost:8000)
- **Streamlit** in `frontend/app.py`: `streamlit run app.py`
- Frontend expects `GET /status/` and `POST /simulate/aftershock` for Aftershock flow
- Port: often 5173 or 5174 (Vite); 8501 (Streamlit)

---

## Important Conventions

1. **Backend runs as package** – `uvicorn backend.main:app` from project root; `uvicorn main:app` from backend/ fails due to relative imports
2. **Backend-only scope** – Do not edit frontend, GeoJSON, Docker, pipelines unless explicitly asked
3. **Mock-first** – Aftershock uses mock JSON; real data via `data/processed/region_panel.parquet` and `models/graph.json`
4. **Clamping** – `delta_funding_pct` [-0.3, 0.3]; `horizon_steps` [1, 2]; shocks [0, 1]

---

## Testing

```bash
pytest backend/tests/test_aftershock.py -v
pytest backend/tests/test_scenario.py -v   # if exists
```

---

## Curl Examples

```bash
# Status
curl http://localhost:8000/status/

# Aftershock
curl -X POST http://localhost:8000/simulate/aftershock \
  -H "Content-Type: application/json" \
  -d '{"epicenter":"BFA","delta_funding_pct":-0.2,"horizon_steps":2}'
```

---

## DataML Handoff – What’s Ready for Backend

### Simulation

- **Import:** `from dataml.src.simulate_aftershock import simulate_aftershock`
- **Endpoint:** `POST /simulate` (or align with existing `/simulate/aftershock`)
- **Request:**
  ```json
  { "country": "BFA", "delta_funding_pct": -0.2, "horizon_steps": 2 }
  ```
- **Call:** `simulate_aftershock(node_iso3=country, delta_funding_pct=delta_funding_pct, horizon_years=horizon_steps)`
- **Return:** The dict from DataML directly as JSON

Note: Current backend uses `epicenter`; DataML uses `country`. Map `epicenter` → `node_iso3` and `horizon_steps` → `horizon_years` when delegating to DataML.

### Baseline + Map Data

- **Paths:** `dataml/data/processed/`
  - `nodes.json` – crisis nodes
  - `edges.json` – edges
  - `baseline_predictions.json` – baseline predictions

Use these for `GET /status` and baseline map rendering instead of `backend/mock_data/`.

### Project Benchmarking (Optional)

- `dataml/data/processed/project_metrics.json`
- `dataml/data/processed/project_neighbors.json`

Can be exposed as:
- `GET /project_metrics`
- `GET /project_neighbors`

### Actian VectorAI (Later)

- **Paths:** `dataml/data/processed/`
  - `crisis_embeddings.parquet`
  - `project_embeddings.parquet`

Schema: each row = `id` + `description` + `embedding` + key metadata. Intended for VectorAI tables behind:
- `/similar_crises`
- `/similar_projects`

### Sphinx Tables (Later)

- `crises_for_sphinx.parquet`
- `projects_for_sphinx.parquet`
- `aftershock_baseline_for_sphinx.parquet`

These are the structured tables Sphinx should attach to for memo generation.

---

## Docs to Read

- `backend/docs/AFTERSHOCK.md` – Aftershock endpoints, request/response, data swap
- `RUN.md` – Run instructions
- `docs/PROJECT_CONTEXT.md` – This file
