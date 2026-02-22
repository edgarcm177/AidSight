# Aftershock Integration Notes

Dev-facing summary for the Aftershock spillover simulation flow. Read this to understand the end-to-end integration in ~5 minutes.

---

## Aftershock API Contract

### Request: `POST /simulate/aftershock`

```json
{
  "epicenter": "BFA",
  "delta_funding_pct": -0.2,
  "horizon_steps": 2
}
```

- **epicenter**: ISO3 country code (e.g. `"BFA"`, `"MLI"`)
- **delta_funding_pct**: Funding change as decimal (`-0.2` = -20%)
- **horizon_steps**: Projection horizon in years (1–2; backend clamps)

### Response: `AftershockResult`

```json
{
  "baseline_year": 2026,
  "epicenter": "BFA",
  "delta_funding_pct": -0.2,
  "horizon_steps": 2,
  "affected": [
    { "country": "NER", "delta_severity": 0.15, "delta_displaced": 45000, "extra_cost_usd": 4500000, "prob_underfunded_next": 0.6 }
  ],
  "totals": {
    "total_delta_displaced": 112000,
    "total_extra_cost_usd": 24000000,
    "affected_countries": 3,
    "max_delta_severity": 0.2
  },
  "notes": []
}
```

---

## Frontend Wiring

### `simulateAftershock` (frontend/src/lib/api.ts)

```ts
simulateAftershock(epicenter: string, deltaFundingPercent: number, horizonMonths: number): Promise<AftershockResult>
```

- **Months → years**: `0–6 months → horizon_steps = 1`, `7–12 months → horizon_steps = 2`
- **Percent → decimal**: `deltaFundingPercent` -20..+20 → `delta_funding_pct` -0.2..+0.2

### Components consuming `AftershockResult`

| Component | Usage |
|-----------|-------|
| **App.tsx** | `handleRunScenario` calls `simulateAftershock`; stores result in `simulationResult` state |
| **ImpactPanel.tsx** | Renders `totals.total_delta_displaced`, `totals.total_extra_cost_usd`; derives underfunded count from `affected` (prob_underfunded_next > 0.5) |
| **map_test.html** | Receives `AFTERSHOCK_AFFECTED` via postMessage; applies shockwave styling (epicenter + affected countries by delta_displaced) |

---

## Memo Behavior

### When TTC/equity sim is placeholder (all zeros)

- Memo **leads** with a labeled **Spillover risk** paragraph
- TTC and equity paragraphs are **omitted**
- Spillover text: funding change, extra IDPs, top affected countries, extra cost, horizon

### When both real TTC/equity and aftershock exist

- TTC and equity paragraphs appear **first**
- A labeled **Spillover risk** paragraph is **appended** after

---

## Data Pipeline (run in order from repo root)

```bash
python -m dataml.scripts.fetch_cbpf
python -m dataml.scripts.fetch_inform_severity
python -m dataml.scripts.fetch_displacement_flows
python -m dataml.scripts.build_nodes_edges
```

**Region**: Sahel (2020–2024). Real CBPF/INFORM/DTM when files present; misfit/stub mode when missing (logged).

**Artifacts** (all under `dataml/data/processed/`):

- `nodes.json`, `edges.json` — used by `GET /status` (map)
- `sahel_panel.parquet`, `spillover_graph.parquet` — used by `simulate_aftershock`

---

## Data Sources & Integrations

### GET /status (map data)

**Order**: 1) Databricks → 2) DataML (nodes.json, edges.json) → 3) backend mock.

- **Databricks enabled**: Reads `aftershock.crisis_metrics`; returns country nodes. On env missing or SQL failure, falls back to DataML.
- **Databricks disabled**: Uses `dataml/data/processed/nodes.json` and `edges.json`; if missing, backend mock.

**Databricks setup:**
- Table expected: `aftershock.crisis_metrics` with columns: country_iso3, year, severity_score, requirements_usd, funding_usd, coverage_pct, pooled_fund_coverage_usd, underfunding_score
- Create from sahel_panel.parquet via Databricks notebook: `spark.read.parquet("path/to/sahel_panel.parquet").write.saveAsTable("aftershock.crisis_metrics")`
- Env vars: `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_HTTP_PATH`

### POST /explain/crisis (Sphinx)

- **Enabled**: POST to `SPHINX_BASE_URL` with `{query, context}`; expects `{answer}` or `{explanation}`. No API key required (optional `SPHINX_API_KEY` for auth).
- **Disabled**: Returns static fallback explanation.

### GET /projects/{id}/vector_neighbors (VectorAI)

- **Enabled**: Queries Actian VectorAI DB when `ACTIAN_VECTORAI_CONNECTION_STRING` and `ACTIAN_PROJECTS_COLLECTION` set; returns `{id, similarity_score, ratio, country, cluster}`.
- **Disabled**: In-memory KNN from `project_embeddings.parquet`; same schema.

---

## Env Vars (Backend)

| Variable | Purpose |
|----------|---------|
| `DATABRICKS_HOST` | Databricks workspace host (e.g. `xxx.azuredatabricks.net`) |
| `DATABRICKS_TOKEN` | Personal access token |
| `DATABRICKS_HTTP_PATH` | SQL warehouse HTTP path |
| `SPHINX_BASE_URL` | Sphinx API base URL (required for Sphinx; no API key needed) |
| `SPHINX_API_KEY` | Optional auth header for Sphinx |
| `ACTIAN_VECTORAI_CONNECTION_STRING` | Actian VectorAI connection |
| `ACTIAN_PROJECTS_COLLECTION` | Collection name for projects |

---

## Known Intentional Limitations

- **Heuristic fallback**: When `spillover_model.pt` is missing (gitignored), DataML uses a graph-based heuristic; simulation still returns valid schema
- **Months→years mapping**: Coarse (0–6m → ~1 year, 7–12m → ~2 years); no finer granularity
- **Backend horizon clamp**: `horizon_steps` clamped to 1–2; `delta_funding_pct` clamped to [-0.3, 0.3]
