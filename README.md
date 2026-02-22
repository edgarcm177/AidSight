# Ripplect

Humanitarian strategy sandbox: crisis data, fragility simulation (TTC, Equity Shift), Success Twins (semantic project matching), and contrarian memos.

**Stack:** Backend: FastAPI (uvicorn). Frontend: Vite + React.

---

## Setup

1. **Build Parquet data** (from repo root):
   ```bash
   python scripts/preprocess.py
   ```
   Produces `backend/data/crises.parquet` and `backend/data/projects.parquet`.

   **Success Twin project data:** The app loads projects from `data/projects.parquet`. If you see "Not enough projects in crisis country MLI" (or BFA/NER/TCD), seed at least 2 projects per epicenter:
   ```bash
   python -m backend.scripts.seed_epicenter_projects
   ```
   This adds synthetic MLI, BFA, NER, TCD projects to `data/projects.parquet` so "Find Success Twin" works for every epicenter.

2. **Backend dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Frontend dependencies:**
   ```bash
   cd frontend && pnpm install
   ```
   Or: `npm install` if you don’t use pnpm.

---

## Run

### Backend

From repo root:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API: http://localhost:8000

### Frontend

```bash
cd frontend && pnpm dev
```

Or: `npm run dev`. App: http://localhost:5173 (or next free port).

Optional: set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env.local` (defaults to that if unset).

---

## Check Data & ML health

Single one-command smoketest (run from repo root):

```bash
python run_smoketest.py
```

Prints a dict of `*_ok` flags and a final line: `All *_ok flags True: True` or `False`. Exit code 0 only if all flags are True. Use before hacking, after pulling, and before demos.

---

## Check API contracts (optional)

Lightweight sanity check of HTTP endpoints (no server needed; uses FastAPI TestClient):

```bash
python backend/check_api_contract.py
```

Verifies GET /crises/, POST /simulate/, GET /twins/PRJ001, POST /memos/. Exits 0 on PASS, 1 on FAIL.

---

## Similar Projects (VectorAI)

The **“Similar Projects (VectorAI)”** feature uses the [Actian VectorAI DB beta](https://github.com/hackmamba-io/actian-vectorAI-db-beta) for nearest-neighbor search over project embeddings. Without it, the backend falls back to in-memory search from parquet.

### 1. Run VectorAI DB

Clone and start the Actian VectorAI DB (gRPC default `localhost:50051`):

```bash
git clone https://github.com/hackmamba-io/actian-vectorAI-db-beta
cd actian-vectorAI-db-beta && docker compose up -d
```

### 2. Install Python client

Install the `actiancortex` wheel from the Actian repo (see that repo’s README for the latest install steps). Example:

```bash
pip install path/to/actian-vectorAI-db-beta/wheels/actiancortex-*.whl
```

### 3. Environment

Set in `.env` or `.env.local` (or export before running backend/ingestion):

| Variable | Example | Description |
|----------|---------|-------------|
| `ACTIAN_VECTORAI_CONNECTION_STRING` | `localhost:50051` | VectorAI gRPC host:port |
| `ACTIAN_PROJECTS_COLLECTION` | `projects` | Collection name for project embeddings |
| `ACTIAN_PROJECTS_DIMENSION` | `5` | (Optional) Embedding dimension; default 5 to match DataML |

### 4. Build embeddings and ingest

Ensure project embeddings exist, then run the ingestion script (from repo root):

```bash
# Build project embeddings (if not already done)
python -m dataml.src.embeddings   # or your DataML pipeline

# Ingest into VectorAI DB
python -m backend.scripts.ingest_vectorai_projects
```

This reads `dataml/data/processed/project_embeddings.parquet` and batch-upserts into the Actian collection. Then “Find similar projects” in the app uses the real vector DB.

---

## Demo flow (3–5 min)

1. **Start** – Open the app. Left panel: “Configure Scenario.”
2. **Pick a crisis** – Choose one from the dropdown (e.g. “GHO Estimates (SYR 2024)”).
3. **Set funding** – Adjust Health Δ and WASH Δ (e.g. -1M Health, +0.5M WASH).
4. **Set shocks** – Optionally change Inflation %, Drought, Conflict level.
5. **Run scenario** – Click “Run Scenario.” Center “Impact” panel shows baseline vs scenario TTC and Equity Shift.
6. **Find Success Twin** – Right panel: click “Find Success Twin” for sample project PRJ001.
7. **Generate memo** – Click “Generate Memo.” Read title, body, and key risks.
8. **Vary inputs** – Change funding or shocks, run again, compare impact and memo.
