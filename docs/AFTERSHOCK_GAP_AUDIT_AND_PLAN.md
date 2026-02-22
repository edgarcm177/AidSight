# Aftershock Gap Audit & Two-Dev Work Plan

**Date:** 2025-02-21  
**Purpose:** Confirm gaps, propose minimal fixes, split into two parallel workstreams. No code edits in this document—analysis and plan only.

---

## PHASE 1 – Current State and Gaps (Confirmed)

### Aftershock UI

| Item | Location | Status |
|------|----------|--------|
| Epicenter dropdown | `frontend/src/app/components/DecisionSandbox.tsx` lines 32–41 | Implemented (MLI, BFA, NER, TCD) |
| Funding slider | `DecisionSandbox.tsx` lines 47–72 | Implemented (-20% to +20%) |
| Horizon slider | `DecisionSandbox.tsx` lines 74–103 | Implemented (0–12 months), label "Short-term / Medium-term" present |
| Run Aftershock handler | `frontend/src/app/App.tsx` `handleRunScenario` lines 65–84 | **Wired** – calls `simulateAftershock` |
| Generate Memo handler | `frontend/src/app/App.tsx` `handleGenerateMemo` lines 104–140 | **Wired** – calls `createMemo` |

### Map

| Item | Location | Status |
|------|----------|--------|
| Base choropleth | `frontend/public/map_test.html` – `L.geoJson` style function | MLI=red, BFA/NER/TCD=green; rest=light green; **no opacity reduction** |
| Aftershock overlay | `map_test.html` `applyAftershockStyling` | Low/medium/high buckets; epicenter distinct; **all affected use same fill color #7f1d1d** |
| Legend | `map_test.html` legend control | Severity & Funding only; **no spillover legend** |

### Memo

| Item | Location | Status |
|------|----------|--------|
| Backend endpoint | `POST /memos/` via `backend/routers/memos.py` | Implemented |
| Request model | `MemoRequest` (crisis_id, simulation, twin?, scenario?, aftershock?) | Implemented |
| Response model | `MemoResponse` (title, body, key_risks) | Implemented |
| Frontend caller | `createMemo` in `api.ts`, used in `handleGenerateMemo` | **Wired** |
| Memo display | `frontend/src/app/components/SuccessTwinPanel.tsx` line 115 | **Bug:** uses `memoResult.memo` – MemoResponse has `body`, not `memo`; memo text never renders |
| Spillover paragraph | `backend/services/memo.py` `_build_aftershock_spillover_paragraph` | Implemented and UN-judge-ready |

### Confirmed Absence / Stub Status

| Integration | Status | Evidence |
|-------------|--------|----------|
| **Databricks** | **None** | No `databricks_client.py`; no `DATABRICKS_*` env vars; `/status/` and map data load from local JSON/Parquet via `dataml_status_data.py` |
| **Sphinx** | **Export only** | `export_sphinx_tables.py` produces Parquet; `/debug/sphinx_preview` reads Parquet; **no Sphinx API client, no Sphinx queries** |
| **Actian VectorAI** | **In-memory stub** | `backend/services/vectorai.py` uses `iter_crisis_embeddings` / `iter_project_embeddings` from Parquet; `search_similar_*` is sklearn cosine; no VectorAI DB connection |
| **Figma Make** | **Scaffold only** | `my-app/` exists; `package.json` name `@figma/my-make-file`; **no export script** for scenario JSON; no dedicated Figma-ready JSON schema |

---

## Current Gaps (Summary)

- **Map expressiveness:** Base choropleth is saturated; Aftershock overlay uses one fill color (#7f1d1d) for all affected; no spillover legend; "all red" feel.
- **Time dimension:** Horizon slider maps to 1 or 2 years; no explicit "T+12m" / "T+24m" labeling in ImpactPanel; no animation.
- **Memo wiring:** `handleGenerateMemo` → `createMemo` is wired, but SuccessTwinPanel renders `memoResult.memo` (doesn't exist); should use `memoResult.body` (and optionally `title`). "Generate Memo" button is visible but memo text does not show.
- **Databricks usage:** None. All data from local Parquet/JSON.
- **Sphinx usage:** Export scripts and debug preview only; no Sphinx API client or "Ask Sphinx why" flow.
- **VectorAI usage:** In-memory stub only; no Actian VectorAI DB.
- **Figma Make:** No export script; no single-scenario JSON for prototype.

---

## PHASE 2 – Minimal Fix Designs

### 2.1 Map: From "All Red" to Clear Spillover

**Design:**
- Reduce base choropleth opacity (e.g. `fillOpacity: 0.5`) for non-affected countries so Aftershock stands out.
- Keep existing low/medium/high buckets; add a distinct color ramp (e.g. amber→red) for low→high spillover instead of single #7f1d1d.
- Add a small spillover legend: "Low / Medium / High spillover" with swatches.

**Files:**
- `frontend/public/map_test.html`
  - In `L.geoJson` style: reduce `fillOpacity` for baseline (e.g. 0.5).
  - In `applyAftershockStyling`: use `fillColor` gradient (e.g. #fbbf24 low, #ef4444 high) by bucket.
  - In legend: add 3 rows for spillover intensity.

---

### 2.2 Time Dimension (Lightweight)

**Design:**
- Use existing horizon slider (0–6 → 1 year, 7–12 → 2 years).
- In ImpactPanel and/or DecisionSandbox:
  - For `timeHorizon <= 6`: show "Impact at T+12m".
  - For `timeHorizon > 6`: show "Impact at T+24m (higher uncertainty)".
- No model changes; UI text only.

**Files:**
- `frontend/src/app/components/DecisionSandbox.tsx` – refine horizon label.
- `frontend/src/app/components/ImpactPanel.tsx` – add T+ label near metrics.

---

### 2.3 Memo UX: Fully Wired and Visible

**Design:**
- Fix SuccessTwinPanel to use `memoResult.body` (and `title` if desired); remove `memoResult.memo`.
- Ensure memo box shows when Aftershock is present; spillover paragraph already comes from backend.
- Optionally show `key_risks` as tags.

**Files:**
- `frontend/src/app/components/SuccessTwinPanel.tsx`: replace `memoResult.memo` with `memoResult.body`; add `memoResult.title` as heading.
- Confirm `handleGenerateMemo` passes `aftershock: simulationResult` when Aftershock is present (already done in App.tsx).

---

### 2.4 Databricks – Minimal but Real Integration

**Design (recommended path):**
- Add `backend/clients/databricks_client.py`:
  - Uses Databricks SQL Connector or REST API.
  - Reads from a Delta table (e.g. `aftershock.crisis_metrics` or `aftershock.crisis_nodes`).
  - Returns list of country nodes (country, severity, funding, etc.).
- Add env vars: `DATABRICKS_HOST`, `DATABRICKS_TOKEN` (or `DATABRICKS_HTTP_PATH`).
- Wire `GET /status/` (or a new `GET /map_state`) to use Databricks client when env vars are set; fall back to `dataml_status_data.get_status_data()` otherwise.
- Document in `docs/AFTERSHOCK_INTEGRATION_NOTES.md`.

**Files:**
- **New:** `backend/clients/databricks_client.py`
- `backend/services/dataml_status_data.py` or `backend/routers/status.py`: conditional Databricks vs local.
- `.env.example`: add `DATABRICKS_HOST`, `DATABRICKS_TOKEN`.

---

### 2.5 Actian VectorAI – Project Doppelgängers

**Design:**
- **Ingest script:** `scripts/ingest_vectorai_projects.py` (or under `dataml/scripts/`):
  - Load `project_embeddings.parquet`.
  - Use Actian VectorAI SDK to upsert into a collection (project_id as ID, embedding vector, metadata).
- **Backend client:** `backend/clients/vectorai_client.py`:
  - Connect to VectorAI DB; query by project_id or embedding; return top-K similar projects.
- **Backend route:** Add `GET /projects/{id}/vector_neighbors` in `backend/routers/projects.py`.
- **Frontend:** In SuccessTwinPanel or a new ProjectDetails section: add "Similar projects (VectorAI)" powered by this endpoint.
- **Fallback:** If VectorAI env vars missing, keep existing twins endpoint (sentence-transformers).

**Files:**
- **New:** `scripts/ingest_vectorai_projects.py` or `dataml/scripts/ingest_vectorai.py`
- **New:** `backend/clients/vectorai_client.py`
- `backend/routers/projects.py`: add `/projects/{id}/vector_neighbors`
- `frontend/src/app/components/SuccessTwinPanel.tsx` (or new component): "Similar projects (VectorAI)" section

---

### 2.6 Sphinx – Reasoning Copilot

**Design:**
- **Backend client:** `backend/clients/sphinx_client.py`:
  - Call Sphinx API with a prompt: "Given crisis X with metrics Y and aftershock totals Z, explain in 2–3 sentences why this crisis may be overlooked compared to neighbors."
  - Use `crises_for_sphinx.parquet` (or Databricks table if 2.4 done) for context.
- **Backend route:** `POST /explain/crisis` (or `GET /explain/crisis?crisis_id=X`) in `backend/routers/explain.py`.
- **Frontend:** Add "Ask Sphinx why" button on memo tab; on click call endpoint; show loading then 2–3 sentences.

**Files:**
- **New:** `backend/clients/sphinx_client.py`
- **New:** `backend/routers/explain.py`
- `frontend/src/app/components/SuccessTwinPanel.tsx`: "Ask Sphinx why" button + result display
- `.env.example`: `SPHINX_API_KEY`, `SPHINX_BASE_URL` (or equivalent)

---

### 2.7 Figma Make – Single Polished Scenario

**Design:**
- **Export script:** `scripts/export_figma_scenario.py`:
  - Runs one Aftershock scenario (e.g. BFA, -20%, horizon 2).
  - Outputs JSON: `{ "baseline": { "nodes": [...], "edges": [...] }, "aftershock": { "affected": [...], "totals": {...} }, "memo_spillover": "Spillover risk: ..." }`.
- **Schema:** Flat, Figma Make–friendly (no nested functions).
- **Figma Make:** Build one prototype using this JSON as data source; before/after map states + key metrics + spillover sentence.

**Files:**
- **New:** `scripts/export_figma_scenario.py`
- **New:** `docs/figma_scenario_schema.json` (schema doc) or sample `scenario_for_figma.json`

---

## PHASE 3 – Two-Dev Workstream Split

### Dev A – Data/ML + Backend + Sponsor Infra

| # | Task | Files | Notes |
|---|------|-------|-------|
| A1 | Databricks client + wiring | **New** `backend/clients/databricks_client.py`; modify `backend/services/dataml_status_data.py` or `backend/routers/status.py` | Read crisis nodes from Delta; fallback to local if env vars missing |
| A2 | VectorAI client + route | **New** `backend/clients/vectorai_client.py`; `backend/routers/projects.py` add `GET /projects/{id}/vector_neighbors` | Query Actian VectorAI for similar projects |
| A3 | VectorAI ingest script | **New** `scripts/ingest_vectorai_projects.py` or `dataml/scripts/ingest_vectorai.py` | Upsert project embeddings into VectorAI collection |
| A4 | Sphinx client + route | **New** `backend/clients/sphinx_client.py`; **New** `backend/routers/explain.py` add `POST /explain/crisis` | One prompt: "Why is this crisis overlooked?" |
| A5 | Figma scenario export script | **New** `scripts/export_figma_scenario.py` | Run one Aftershock; output JSON for Figma Make |
| A6 | Env and docs | `.env.example`; `docs/AFTERSHOCK_INTEGRATION_NOTES.md` | Document DATABRICKS_*, VECTORAI_*, SPHINX_* |

---

### Dev B – Frontend + UX + Story

| # | Task | Files | Notes |
|---|------|-------|-------|
| B1 | Fix memo display bug | `frontend/src/app/components/SuccessTwinPanel.tsx` | Replace `memoResult.memo` with `memoResult.body` (+ `title`); ensure memo is visible |
| B2 | Map: base opacity + spillover ramp + legend | `frontend/public/map_test.html` | Reduce base fillOpacity; color ramp for low/med/high; add spillover legend |
| B3 | Time labels (T+12m / T+24m) | `frontend/src/app/components/DecisionSandbox.tsx`, `ImpactPanel.tsx` | "Impact at T+12m" / "Impact at T+24m (higher uncertainty)" |
| B4 | SuccessTwinPanel: wire affected from simulation | `frontend/src/app/components/SuccessTwinPanel.tsx` | Replace hardcoded NER/BFA/TCD list with `simulationResult?.affected`; format delta_displaced, extra_cost_usd |
| B5 | "Ask Sphinx why" button | `frontend/src/app/components/SuccessTwinPanel.tsx` | Button on memo tab; call `POST /explain/crisis`; show loading + result |
| B6 | "Similar projects (VectorAI)" section | `frontend/src/app/components/SuccessTwinPanel.tsx` or new component | Call `GET /projects/{id}/vector_neighbors`; render list |
| B7 | Figma Make prototype | Manual in Figma | Use JSON from `scripts/export_figma_scenario.py`; before/after map + metrics + spillover |

---

## Quick Checklist for Handoff

**Dev A (pick these):**
- [ ] A1 Databricks client + status/map_state wiring
- [ ] A2 VectorAI client + `/projects/{id}/vector_neighbors`
- [ ] A3 VectorAI ingest script
- [ ] A4 Sphinx client + `/explain/crisis`
- [ ] A5 `scripts/export_figma_scenario.py`
- [ ] A6 Env + docs

**Dev B (pick these):**
- [ ] B1 Fix `memoResult.memo` → `memoResult.body` (and `twinResult.project_id` → `twinResult.twin_project_id` if needed)
- [ ] B2 Map: base opacity, spillover color ramp, legend
- [ ] B3 Time labels T+12m / T+24m
- [ ] B4 Wire SuccessTwinPanel "Affected Countries" from `simulationResult.affected`
- [ ] B5 "Ask Sphinx why" button
- [ ] B6 "Similar projects (VectorAI)" section
- [ ] B7 Figma Make prototype

**Suggested order (both in parallel):**
- Dev A: A5 (export script) first so Dev B can use JSON for B7; then A1–A4, A6.
- Dev B: B1 (memo fix) first for immediate UX; then B2–B4; B5–B6 when A4/A2 are ready; B7 when A5 is done.
