# AFTERSHOCK PROJECT STATE REPORT

**Analysis Date:** 2025-02-21  
**Repository:** AidSight (Hacklytics humanitarian crisis prediction platform)

---

## EXECUTIVE SUMMARY

AidSight/Aftershock is a portfolio stress-testing and spillover simulation tool for humanitarian funding. The backend (FastAPI), DataML pipeline (PyTorch GNN, preprocess, simulate_aftershock), and frontend (Vite + React) are largely implemented. **The primary blocker is that the frontend never calls the aftershock simulation API**—"Run Aftershock" uses a mock 1.5s timeout and fake success. The backend `/simulate/aftershock` endpoint exists and works; the DataML `simulate_aftershock()` function is callable and returns the expected schema.

**Completion Estimate:** ~70% complete  
**Critical Blockers:** (1) Frontend not wired to aftershock API; (2) Data path inconsistencies; (3) Model weights (spillover_model.pt) gitignored—requires local training.  
**Ready for Demo:** NO—core aftershock flow shows hardcoded metrics.

---

## 1. REPOSITORY STRUCTURE

### 1.1 Directory Structure

| Path | Purpose |
|------|---------|
| `backend/` | FastAPI app, routers (crises, simulate, twins, memos, status, project_benchmarking, projects, vectorai, debug), services |
| `backend/data/` | Re-exports `data.data_loader` (from top-level `data` package)—no local Parquet files |
| `backend/routers/` | crises, simulate, twins, memos, status, project_benchmarking, projects, vectorai_routes, debug |
| `backend/services/` | aftershock_engine, aftershock_data, dataml_client, fragility, memo, twins, vectorai, healthcheck, data_loader, dataml_status_data, scenarios |
| `backend/scripts/` | preprocess (writes to `backend/data/`) |
| `backend/mock_data/` | aftershock_graph.json, aftershock_panel.json (mock Sahel) |
| `data/` | Crises/projects package—`data_loader.py` loads `data/crises.parquet`, `data/projects.parquet` |
| `dataml/` | Data/ML: preprocess, train, simulate_aftershock, graph, projects, embeddings |
| `dataml/data/raw/` | misfit_final_analysis.csv (HNO/HRP-style Sahel input) |
| `dataml/data/processed/` | sahel_panel, spillover_graph, nodes.json, edges.json, baseline_predictions.json, project_metrics.json, project_neighbors.json, Sphinx parquets, embeddings |
| `dataml/models/` | model_config.json; spillover_model.pt (gitignored) |
| `dataml/scripts/` | run_preprocess, run_train, run_aftershock_smoketest, export_baseline_structures, export_project_benchmarking, export_sphinx_tables |
| `frontend/` | Vite + React, DecisionSandbox, ImpactPanel, SuccessTwinPanel |
| `my-app/` | Next.js scaffold (Figma/Make alternate) |
| `apps/web/` | Web app scaffold (if present) |
| `docs/` | PROJECT_CONTEXT.md |

### 1.2 Orphaned / Inconsistent Items

- **backend/services/data_loader.py**: Uses `DATA_DIR = backend/services/`; no routers import it. Active loader is `data.data_loader` via `backend.data`.
- **README** says `python scripts/preprocess.py`; actual script is `python -m backend.scripts.preprocess`. No root-level `scripts/preprocess.py`.
- **Data path mismatch**: Backend preprocess writes to `backend/data/crises.parquet`, `backend/data/projects.parquet`; `data.data_loader` loads from `data/crises.parquet`, `data/projects.parquet`. Two different pipelines.
- **my-app/** and **apps/web/**: Alternate scaffolds; role vs main `frontend/` unclear.

---

## 2. DATA PIPELINE

### 2.1 Data Sources

| Source | Status | Location |
|--------|--------|----------|
| **HNO/HRP** | Present | data/raw/humanitarian-response-plans.csv, hpc_hno_2026.csv; dataml/data/raw/misfit_final_analysis.csv |
| **INFORM-style** | Proxy in code | Severity proxy = relative need increase (simulate_aftershock, preprocess) |
| **Underfunded** | Present | chronic_underfunded_flag, underfunding_score in preprocess and Sphinx tables |
| **CBPF / DTM** | Not found | No direct references |

### 2.2 Data Processing Scripts

| Script | Purpose | Input | Output | Status |
|--------|---------|-------|--------|--------|
| backend/scripts/preprocess.py | Crises/projects for TTC/Twin | backend/data/raw/misfit_final_analysis.csv, projects_sample.csv | backend/data/crises.parquet, projects.parquet | Implemented; output not used by loader |
| dataml/scripts/run_preprocess.py | Sahel panel, spillover graph | misfit_final_analysis.csv, spillover_edges.csv | sahel_panel.parquet, spillover_graph.parquet, features.parquet | Implemented |
| dataml/scripts/run_train.py | GNN training | sahel_panel, spillover_graph | spillover_model.pt, model_config.json | Implemented; .pt gitignored |
| dataml/scripts/export_baseline_structures.py | Map/status data | sahel_panel, spillover_graph, model | nodes.json, edges.json, baseline_predictions.json | Implemented |
| dataml/scripts/export_project_benchmarking.py | Project benchmarking | project_metrics.parquet, project_neighbors.parquet | project_metrics.json, project_neighbors.json | Implemented |
| dataml/scripts/export_sphinx_tables.py | Sphinx/Databricks + Actian | sahel_panel, project_metrics, baseline | crises_for_sphinx, projects_for_sphinx, aftershock_baseline_for_sphinx, embeddings | Implemented |

### 2.3 Processed Artifacts

| File | Schema (sample) | Status |
|------|-----------------|--------|
| nodes.json | country, year, severity, funding_total_usd, beneficiaries_total, underfunding_score, chronic_underfunded_flag | Present; dataml_status_data maps to CountryBaseline |
| edges.json | source_country, target_country, weight | Present; dataml_status_data maps src/dst |
| baseline_predictions.json | country, baseline_year, severity_pred_baseline, displacement_in_pred_baseline | Present |
| project_metrics.json | project-level metrics | Present |
| project_neighbors.json | similarity data | Present |

**.gitignore:** `*.parquet`, `*.pt`, `*.pkl` are ignored. Parquet and model weights are not versioned; first-time setup requires running pipelines locally.

---

## 3. ML MODEL

### 3.1 Model Code

- **Framework:** PyTorch (GNN)
- **Model files:** `dataml/src/train.py` (SpilloverGNN), `dataml/src/simulate_aftershock.py`
- **Weights:** spillover_model.pt (gitignored)
- **Config:** model_config.json (nodes, node_to_idx, in_dim=5, hidden_dim=32, out_dim=2)

### 3.2 Training Status

| Item | Path | Status |
|------|------|--------|
| Training script | dataml/scripts/run_train.py, dataml/src/train.py | Found |
| Config | dataml/models/model_config.json | Found |
| Weights | dataml/models/spillover_model.pt | Gitignored; must run train locally |
| Logs | None | N/A |

### 3.3 simulate_aftershock

| Property | Value |
|----------|-------|
| **Location** | dataml/src/simulate_aftershock.py |
| **Signature** | `simulate_aftershock(node_iso3: str, delta_funding_pct: float, horizon_years: int) -> Dict[str, Any]` |
| **Inputs** | ISO3 code, funding change (-0.2 = -20%), horizon years (1–10) |
| **Output** | baseline_year, epicenter, delta_funding_pct, affected, total_extra_displaced, total_extra_cost_usd, notes |
| **Callable** | YES (falls back to heuristic if model missing) |
| **Backend integration** | dataml_client.run_simulate_aftershock → simulate.py POST /simulate/aftershock |

---

## 4. BACKEND API

### 4.1 Framework

- **Stack:** FastAPI, Pydantic v2
- **App:** backend/main.py
- **Port:** 8000 (default uvicorn)

### 4.2 Endpoint Inventory

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | / | root | Health check |
| GET | /crises/ | list_crises | List crises (from data/crises.parquet) |
| GET | /crises/{id} | get_crisis | Get crisis by id |
| GET | /crises/nodes | get_nodes | nodes.json |
| GET | /crises/edges | get_edges | edges.json |
| GET | /crises/baseline_predictions | get_baseline_predictions | baseline_predictions.json |
| POST | /simulate/shock | simulate_shock | DataML simulate (country, delta_funding_pct, horizon_steps) |
| POST | /simulate/ | simulate_scenario | Fragility sim (crisis_id, funding_changes, shock) |
| POST | /simulate/aftershock | simulate_aftershock_route | **Aftershock spillover** (epicenter, delta_funding_pct, horizon_steps) |
| GET | /twins/{project_id} | get_success_twin | Success Twin |
| POST | /memos/ | generate_memo | Generate contrarian memo |
| GET | /status/ | get_status | Baseline status (countries, edges) for map |
| GET | /project_benchmarking/project_metrics | get_project_metrics | project_metrics.json |
| GET | /project_benchmarking/project_neighbors | get_project_neighbors | project_neighbors.json |
| GET | /projects/metrics | get_metrics | project_metrics.json |
| GET | /projects/neighbors/{project_id} | get_neighbors_by_project | Neighbors for project |
| GET | /vectorai/similar_crises | similar_crises | Stub (in-memory cosine) |
| GET | /vectorai/similar_projects | similar_projects | Stub (in-memory cosine) |
| GET | /debug/sphinx_preview | sphinx_preview | Sphinx parquet preview |

### 4.3 Database / External Services

- **Database:** None; uses Parquet/JSON files
- **Actian VectorAI:** Stub in vectorai.py (in-memory cosine on embeddings parquet); no connection configured
- **Sphinx AI:** Export scripts produce Sphinx-ready parquets; no Sphinx API integration
- **Databricks:** Referenced in docs; no connection code

---

## 5. FRONTEND

### 5.1 Framework

- **Stack:** Vite + React
- **Build:** vite.config.ts (port 5173)
- **Styling:** Tailwind, Radix UI, MUI
- **TypeScript:** Yes

### 5.2 Component Inventory

| Component | Path | Purpose | API Calls |
|-----------|------|---------|-----------|
| App.tsx | frontend/src/app/App.tsx | Root layout, state, panels | fetchCrises, simulate (unused for aftershock), fetchTwin, createMemo |
| DecisionSandbox | frontend/src/app/components/DecisionSandbox.tsx | Epicenter, funding slider, time horizon, Run Aftershock | None (parent calls onRunScenario) |
| ImpactPanel | frontend/src/app/components/ImpactPanel.tsx | Map iframe, impact metrics | None |
| SuccessTwinPanel | frontend/src/app/components/SuccessTwinPanel.tsx | Success Twin, memo, affected countries | fetchTwin, createMemo |

### 5.3 API Integration

- **Base URL:** `VITE_API_BASE_URL` (default http://localhost:8000)
- **api.ts:** fetchCrises, simulate (POST /simulate/ – fragility), fetchTwin, createMemo
- **No aftershock client:** api.ts has no `simulateAftershock()` calling POST /simulate/aftershock

### 5.4 UI Features Status

| Feature | Status | Notes |
|---------|--------|-------|
| Map visualization | Partial | Iframe; needs verification |
| Epicenter dropdown | Implemented | MLI, BFA, NER, TCD |
| Funding slider | Implemented | -20% to +20% |
| Time horizon slider | Implemented | 0–12 months (backend uses years 1–2) |
| Run Aftershock button | **Stub** | 1.5s mock delay; no API call |
| Impact metrics | **Hardcoded** | +112,000, +$24.0M, +2 |
| Success Twin | Implemented | Wired to backend |
| Memo generation | Implemented | Wired to backend |

---

## 6. INTEGRATION ANALYSIS

### 6.1 End-to-End Data Flow

```
RAW DATA (misfit_final_analysis.csv, etc.)
  → dataml preprocess → sahel_panel.parquet, spillover_graph.parquet
  → dataml train → spillover_model.pt (gitignored)
  → dataml simulate_aftershock → {baseline_year, epicenter, affected, totals, ...}
       ↓
  BACKEND dataml_client → run_simulate_aftershock
       ↓
  POST /simulate/aftershock → AftershockResult
       ↓
  FRONTEND: NOT CONNECTED — handleRunScenario uses mock, ImpactPanel shows hardcoded values
```

### 6.2 Schema Consistency

| Layer | Format | Status |
|-------|--------|--------|
| DataML output | baseline_year, epicenter, delta_funding_pct, affected, total_extra_displaced, total_extra_cost_usd | ✓ |
| dataml_client | Maps to totals (total_delta_displaced, total_extra_cost_usd, affected_countries, max_delta_severity) | ✓ |
| AftershockResult | baseline_year, epicenter, delta_funding_pct, horizon_steps, affected, totals | ✓ |
| Frontend | No AftershockResult type; SimulationResult used for fragility | ✗ Mismatch |

### 6.3 Missing Links

1. **Frontend DecisionSandbox → Aftershock API**  
   - `handleRunScenario` never calls `/simulate/aftershock`  
   - Uses 1.5s mock delay and fake `{ status: 'success' }`  
   - ImpactPanel expects simulation metrics but gets no real aftershock data

2. **api.ts**  
   - No `simulateAftershock(epicenter, deltaFundingPct, horizonSteps)`  
   - No `AftershockResult` or equivalent TypeScript type

3. **Time horizon units**  
   - Frontend: 0–12 months  
   - Backend: 1–2 years (horizon_steps clamped)  
   - Need conversion or alignment

---

## 7. CONFIGURATION

### 7.1 Environment Variables

| Variable | Purpose | Status |
|----------|---------|--------|
| VITE_API_BASE_URL | Frontend API base | .env.example exists; defaults to http://localhost:8000 |
| Backend env | None documented | No DATABASE_URL, ACTIAN_*, SPHINX_*, etc. |

### 7.2 Dependencies

- **Backend:** requirements.txt (fastapi, uvicorn, pydantic, pandas, pyarrow, numpy, sentence-transformers, scikit-learn)
- **dataml:** requirements.txt (pandas, pyarrow, numpy, torch)
- **Frontend:** package.json (Vite, React 18, Radix, MUI, Recharts)

### 7.3 Dev Setup

- **Docker:** No Dockerfile or docker-compose.yml
- **Run instructions:** README and docs/PROJECT_CONTEXT.md
- **Smoketest:** python run_smoketest.py (root); python -m dataml.scripts.run_aftershock_smoketest

---

## 8. TRACK ALIGNMENT (Databricks x UN, Actian, Sphinx, Figma)

| Deliverable | Status |
|-------------|--------|
| Overlooked crisis map (severity/funding mismatch) | Partial—underfunding in nodes/Sphinx; map needs verification |
| Project outlier flagging | Implemented—outlier_flag in projects_for_sphinx, project_metrics |
| Comparable project benchmarking | Implemented—project_neighbors, /projects/neighbors/{id} |
| Actian VectorAI | Stub—in-memory cosine; export scripts produce embeddings parquet |
| Sphinx tables | Exported—crises_for_sphinx, projects_for_sphinx, aftershock_baseline; no Sphinx API |
| Figma Make | my-app/ scaffold present; export/prototype status unclear |

---

## CRITICAL ISSUES SUMMARY

### Integration Gaps

| Gap | Components | Impact | Blocking |
|-----|------------|--------|----------|
| Frontend not calling aftershock API | DecisionSandbox, ImpactPanel, api.ts | HIGH | Core demo flow non-functional |
| Data path mismatch | backend preprocess vs data_loader | MEDIUM | Confusion; backend/data output unused |
| No AftershockResult type in frontend | api.ts, App, ImpactPanel | MEDIUM | Type safety and correct display |

### Missing Components

| Component | Required By | Priority |
|-----------|-------------|----------|
| simulateAftershock() in api.ts | handleRunScenario | HIGH |
| ImpactPanel consumption of real aftershock result | Demo | HIGH |
| spillover_model.pt | DataML (optional; heuristic fallback exists) | MEDIUM |
| Docker setup | Deployment | LOW |

### Schema Mismatches

| Between | Current | Fix |
|---------|---------|-----|
| Frontend SimulationResult vs AftershockResult | Frontend uses SimulationResult (TTC, equity) for fragility; aftershock needs totals, affected | Add AftershockResult type; call /simulate/aftershock; pass result to ImpactPanel |
| Time horizon (months vs years) | Frontend 0–12 months; backend 1–2 years | Map months→years or align units |

---

## IMMEDIATE NEXT STEPS (Priority Order)

### 1. Wire Frontend to Aftershock API (HIGH)

- Add `simulateAftershock(epicenter, deltaFundingPct, horizonSteps)` to api.ts
- Add `AftershockResult` (or equivalent) interface
- In handleRunScenario, call simulateAftershock instead of mock; pass result to ImpactPanel
- ImpactPanel: render real affected countries, totals (displaced, cost, severity)

**Why:** Core demo flow. Blocks end-to-end validation.

**Estimated:** 2–4 hours

### 2. Align Time Horizon (MEDIUM)

- Map frontend months (0–12) to backend horizon_steps (1–2) or extend backend range
- Document mapping in api.ts

**Why:** Avoid silent mis-specification.

**Estimated:** ~30 min

### 3. Resolve Data Path Inconsistency (MEDIUM)

- Option A: Have backend preprocess write to `data/` so data_loader consumes it
- Option B: Update README and document that data/ is populated separately (e.g., from dataml or manual)

**Estimated:** 1 hour

### 4. Ensure Model Artifacts Available (MEDIUM)

- Run `python -m dataml.scripts.run_aftershock_smoketest` to generate spillover_model.pt and parquets
- Or document that heuristic fallback is acceptable for demo

**Estimated:** ~30 min (if training succeeds)

---

## QUESTIONS FOR PROJECT TEAM

1. **Data pipeline:** Should backend/scripts/preprocess populate `data/` (used by crises router) or is there a separate process?
2. **Primary UI:** Is the main app `frontend/` (Vite) or `frontend/app.py` (Streamlit)?
3. **Figma Make / my-app:** What is the intended role of my-app vs frontend?
4. **Actian / Sphinx:** Are live Actian and Sphinx integrations required for the demo, or are stubs/exported tables sufficient?
