# AFTERSHOCK INTEGRATION ANALYSIS

**Analysis Date:** 2025-02-21  
**Purpose:** Document current implementation and integration gaps for the next "fix wiring" prompt. No code changes; analysis only.

---

## 0. Ground Truth Interfaces (From Report + Code Verification)

### Backend Endpoint

| Property | Value |
|----------|-------|
| **Path** | `/simulate/aftershock` (prefix `/simulate` from router → full path `POST /simulate/aftershock`) |
| **Method** | POST |
| **Request shape** | `AftershockParams`: `{ epicenter: str, delta_funding_pct: float, horizon_steps: int = 2, region_scope?: string[], cost_per_person?: float, debug?: bool }` |
| **Response shape** | `AftershockResult`: `{ baseline_year: int, epicenter: str, delta_funding_pct: float, horizon_steps: int, affected: AffectedCountryImpact[], totals: TotalsImpact, graph_edges_used?: EdgeImpact[], notes: string[] }` |
| **TotalsImpact** | `{ total_delta_displaced: float, total_extra_cost_usd: float, affected_countries: int, max_delta_severity: float }` |
| **AffectedCountryImpact** | `{ country: str, delta_severity: float, delta_displaced: float, extra_cost_usd: float, prob_underfunded_next: float, explanation?: string }` |

### DataML simulate_aftershock()

| Property | Value |
|----------|-------|
| **Module** | `dataml.src.simulate_aftershock` |
| **Function signature** | `simulate_aftershock(node_iso3: str, delta_funding_pct: float, horizon_years: int) -> Dict[str, Any]` |
| **Expected inputs** | ISO3 code (e.g. "BFA"), funding change in decimal (-0.2 = -20%), horizon years 1–10 |
| **Outputs** | `{ baseline_year, epicenter, delta_funding_pct, affected, total_extra_displaced, total_extra_cost_usd, notes }` — no `totals`; backend `dataml_client` builds `totals` from these |

### Known Path Mismatches

- **Data:** Backend preprocess writes to `backend/data/crises.parquet`, `backend/data/projects.parquet`; `data.data_loader` reads from `data/crises.parquet`, `data/projects.parquet`. Two separate pipelines.
- **Backend/data package:** `backend/data/__init__.py` re-exports `data.data_loader` (top-level `data` package), not local backend data.

### Model Status (Trained vs Heuristic)

- **Trained model:** `dataml/models/spillover_model.pt` — gitignored; must run `run_train` locally.
- **Heuristic fallback:** `_load_model_and_config()` returns `(None, None, None)` when `.pt` or `model_config.json` missing; `simulate_aftershock` uses `_heuristic_spillover()` instead of `_run_model_forward()`.
- **In practice:** If `.pt` is absent (typical for fresh clone), heuristic is used; simulation still returns valid schema.

---

## 1. Current Frontend Aftershock Wiring

### Handler: handleRunScenario

| Property | Value |
|----------|-------|
| **File** | `frontend/src/app/App.tsx` |
| **Lines** | 63–83 |
| **Behavior** | Mock delay / fake result confirmed. Uses `setSimulationLoading(true)`, `setSimulationError(null)`, `await new Promise(resolve => setTimeout(resolve, 1500))`, `setSimulationResult({ status: 'success' } as any)`. No API call. |

### API Client

| Property | Value |
|----------|-------|
| **File** | `frontend/src/lib/api.ts` |
| **simulateAftershock()** | **MISSING** |
| **Existing `simulate()`** | Calls `POST /simulate/` with `ScenarioPayload` (crisis_id, funding_changes, shock) — fragility sim, not aftershock. |
| **Equivalent for aftershock** | None. No function exists that calls `/simulate/aftershock`. |

### Direct fetch/axios to aftershock endpoint

- **None.** No fetch/axios to `/simulate/aftershock` anywhere in frontend.

---

## 2. Current Backend & DataML Aftershock Path

### Backend Endpoint

| Property | Value |
|----------|-------|
| **File** | `backend/routers/simulate.py` |
| **Framework** | FastAPI |
| **Route** | `POST /aftershock` (router mounted at `/simulate` → full path `POST /simulate/aftershock`) |
| **Request model** | `AftershockParams` (epicenter, delta_funding_pct, horizon_steps, optional region_scope, cost_per_person, debug) |
| **Response model** | `AftershockResult` (baseline_year, epicenter, delta_funding_pct, horizon_steps, affected, totals, graph_edges_used?, notes) |
| **Calls DataML** | Yes — via `run_simulate_aftershock()` in `backend/services/dataml_client.py` (lines 65–69). Falls back to `aftershock_engine` if DataML import/runtime fails. |

### DataML simulate_aftershock()

| Property | Value |
|----------|-------|
| **File + function** | `dataml/src/simulate_aftershock.py` → `simulate_aftershock()` |
| **Signature** | `simulate_aftershock(node_iso3: str, delta_funding_pct: float, horizon_years: int) -> Dict[str, Any]` |
| **Input semantics** | `node_iso3`: ISO3; `delta_funding_pct`: decimal (-0.2) or percent (-20), auto-normalized; `horizon_years`: 1–10 |
| **Return schema** | `{ baseline_year, epicenter, delta_funding_pct, affected, total_extra_displaced, total_extra_cost_usd, notes }`. Each `affected` entry: `{ country, delta_severity, delta_displaced, extra_cost_usd, prob_underfunded_next }`. |

### Noted Mismatches with Frontend

| Aspect | Frontend | Backend/DataML |
|--------|----------|----------------|
| **epicenter vs country** | Uses `epicenter` (same as backend request) | DataML uses `node_iso3`; backend maps epicenter → country for dataml_client |
| **delta_funding_pct** | Slider -20 to +20 (percent) | Backend expects decimal; clamps to [-0.3, 0.3]. Need to send -0.2 for -20%. |
| **horizon** | Slider 0–12 **months** | Backend `horizon_steps` clamped to 1–2 **years**. DataML accepts 1–10 years. |
| **Time units** | Months (0–12) | Years/steps (1–2 effective) |

---

## 3. Frontend vs Backend Contract Mismatches

### Request

| Concept | Frontend (current/expected) | Backend (actual) | Status |
|---------|-----------------------------|------------------|--------|
| Endpoint URL | Not called | `POST /simulate/aftershock` | mismatch (not wired) |
| Epicenter ID | `epicenter` state: "MLI", "BFA", "NER", "TCD" | `epicenter: str` (ISO3) | match (same values) |
| Funding delta | `fundingAdjustment`: -20..+20 (percent) | `delta_funding_pct: float` in decimal (-0.2 for -20%) | mismatch (units) |
| Horizon | `timeHorizon`: 0..12 (months) | `horizon_steps: int` 1–2 (years, clamped) | mismatch (units + range) |

### Response

| Field | Backend field name/type | Frontend usage/expectation | Status |
|-------|-------------------------|----------------------------|--------|
| Total extra IDPs | `totals.total_delta_displaced` (float) | ImpactPanel expects "Extra displaced" — currently hardcoded `+112,000` | mismatch (not consumed) |
| Extra cost USD | `totals.total_extra_cost_usd` (float) | ImpactPanel expects "Extra response cost" — currently hardcoded `+$24.0M` | mismatch (not consumed) |
| Extra underfunded crises | Derived from `affected` (count where prob_underfunded_next crosses threshold) | ImpactPanel expects "New underfunded crises" — currently hardcoded `+2` | mismatch (not derived; no direct field) |
| Per-country severity/disp | `affected[]`: `delta_severity`, `delta_displaced`, etc. | ImpactPanel does not render per-country; map may use for visualization | mismatch (not consumed) |

---

## 4. Verification of Known Issues

### 1) ImpactPanel hardcoded metrics

| Property | Value |
|----------|-------|
| **File** | `frontend/src/app/components/ImpactPanel.tsx` |
| **Lines** | 66–84 |
| **Hardcoded values** | `+112,000` (extra displaced), `+$24.0M` (extra cost), `+2` (new underfunded crises). Displayed when `hasScenario` is true; uses `simulationLoading ? '...' : '+112,000'` etc. |
| **How it should be wired** | Receive `AftershockResult` (or equivalent) as prop; render `totals.total_delta_displaced`, `totals.total_extra_cost_usd`, and a derived count of "new underfunded" (e.g. `affected.filter(a => a.prob_underfunded_next > 0.5).length` or similar). |

### 2) Data path mismatch

| Property | Value |
|----------|-------|
| **Writer path(s)** | `backend/scripts/preprocess.py` → `REPO_ROOT / "backend" / "data"` → `backend/data/crises.parquet`, `backend/data/projects.parquet` |
| **Reader path(s)** | `data/data_loader.py` → `DATA_DIR = Path(__file__).resolve().parent` = `data/` → `data/crises.parquet`, `data/projects.parquet` |
| **Confirmed mismatch** | Yes. Writer outputs to `backend/data/`; reader loads from top-level `data/`. Backend routers use `data.data_loader` (via `backend.data`), so they read from `data/`. Output of backend preprocess is never used by the app unless files are manually copied. |

### 3) Model file & heuristic fallback

| Property | Value |
|----------|-------|
| **.gitignore entry** | Line 46: `*.pt` |
| **Model load code** | `dataml/src/simulate_aftershock.py`, `_load_model_and_config()` (lines 49–69). Checks `MODEL_PATH.exists()` and `CONFIG_PATH.exists()`; returns `(None, None, None)` if missing. |
| **Fallback description** | When model is None, `simulate_aftershock` calls `_heuristic_spillover()` (lines 212–258): graph-based spillover to neighbors, coverage/need updates from shock magnitude. Returns same schema as GNN path. |

### 4) Time horizon mismatch

| Property | Value |
|----------|-------|
| **Frontend definition** | `frontend/src/app/components/DecisionSandbox.tsx` lines 84–93: `min="0" max="12" step="1"`; label "X Months". Range 0–12 months. |
| **Backend definition** | `backend/routers/simulate.py` line 61: `horizon = max(1, min(2, payload.horizon_steps))`. Clamped to 1–2. Passed as `horizon_steps` (conceptually years) to DataML. |
| **Nature of mismatch** | Frontend: months, 0–12. Backend: years/steps, clamped 1–2. No conversion. Sending `timeHorizon=12` (months) would be passed as `horizon_steps=12` then clamped to 2. |

---

## 5. Snapshot for Next Integration Prompt

### Frontend "Run Aftershock" currently

| Property | Value |
|----------|-------|
| **Location** | `frontend/src/app/App.tsx`, `handleRunScenario` (lines 63–83) |
| **Uses mock** | Yes. 1.5s setTimeout, then `setSimulationResult({ status: 'success' } as any)`. No API call. |
| **Needs to call endpoint** | `POST /simulate/aftershock` |

### Backend endpoint

| Property | Value |
|----------|-------|
| **Method + path** | `POST /simulate/aftershock` |
| **Expected body** | `{ epicenter: string, delta_funding_pct: number, horizon_steps?: number }` — `delta_funding_pct` in decimal (-0.2 for -20%); `horizon_steps` clamped 1–2 on backend |
| **Response schema (fields used in UI)** | `totals.total_delta_displaced`, `totals.total_extra_cost_usd`, `affected` (for per-country and for deriving "new underfunded crises" count), `baseline_year`, `epicenter`, `delta_funding_pct`, `horizon_steps`, `notes` |

### Minimal TypeScript interfaces to introduce

```typescript
interface AftershockRequest {
  epicenter: string;        // ISO3
  delta_funding_pct: number; // decimal, e.g. -0.2 for -20%
  horizon_steps?: number;   // 1–2 (backend clamps); map months→years as needed
}

interface AffectedCountryImpact {
  country: string;
  delta_severity: number;
  delta_displaced: number;
  extra_cost_usd: number;
  prob_underfunded_next: number;
  explanation?: string;
}

interface TotalsImpact {
  total_delta_displaced: number;
  total_extra_cost_usd: number;
  affected_countries: number;
  max_delta_severity: number;
}

interface AftershockResult {
  baseline_year: number;
  epicenter: string;
  delta_funding_pct: number;
  horizon_steps: number;
  affected: AffectedCountryImpact[];
  totals: TotalsImpact;
  graph_edges_used?: unknown[];
  notes: string[];
}
```

### Most important 2–3 mismatches to resolve first

1. **Wire frontend to API:** Add `simulateAftershock(epicenter, deltaFundingPct, horizonSteps)` in `api.ts`; call it from `handleRunScenario`; pass result to `ImpactPanel` instead of fake `{ status: 'success' }`. Convert `fundingAdjustment` (-20..+20) to `delta_funding_pct` (-0.2..+0.2).
2. **ImpactPanel consumes real data:** Replace hardcoded `+112,000`, `+$24.0M`, `+2` with `totals.total_delta_displaced`, `totals.total_extra_cost_usd`, and a derived "new underfunded" count from `affected` (e.g. count where `prob_underfunded_next` > threshold). Use `SimulationResult | AftershockResult` union or separate prop for aftershock.
3. **Time horizon mapping:** Map frontend months (0–12) to backend years (1–2). Simple mapping: e.g. 0–6 months → 1, 7–12 months → 2. Or document and use `Math.max(1, Math.min(2, Math.ceil(timeHorizon / 6)))` for horizon_steps.
