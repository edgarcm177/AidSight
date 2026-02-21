# AidSight Architecture

## Flow Overview

```
Data (mock JSON / future Databricks)
    │
    ▼
DataProvider ──► Regions, Projects
    │
    ├──► Scenario Engine ──► Stress Test Results (updated metrics, suggested allocations, regret)
    │
    ├──► Vector Service ──► Comparable Trades (Actian VectorAI or fake)
    │
    └──► Memo Service ──► IC Memo + Red Team (Sphinx AI or fake)
    │
    ▼
API (FastAPI) ──► Frontend (Next.js)
```

## Data Flow

1. **Data** is loaded by `DataProvider`. The `MockDataProvider` reads `regions.json` and `projects.json` from `/apps/api/mock_data/`. To swap in real data, implement a `DatabricksDataProvider` or `ParquetDataProvider` that conforms to the `DataProvider` interface and returns `RegionMetric` and `Project` instances.

2. **Scenario Engine** takes baseline regions and `ScenarioParams` (inflation_shock, climate_shock, access_shock, funding_delta). It applies stress transforms and runs a rebalance heuristic to suggest allocations. Outputs `ScenarioResult` with updated metrics, top downside regions, suggested allocations, and regret score.

3. **Vector Service** provides similarity search over project descriptions. `FakeVectorService` returns deterministic placeholder comparables. To plug in Actian, set `ACTIAN_ENDPOINT` and `ACTIAN_API_KEY`, then implement `RealActianVectorClient.upsert_vectors` and `query_similar` with real HTTP calls.

4. **Memo Service** generates structured memo sections from context (scenario, project, comparables). `FakeSphinxClient` returns deterministic placeholder text. To plug in Sphinx AI, set `SPHINX_ENDPOINT` and `SPHINX_API_KEY`, then implement `RealSphinxClient.generate_memo`.

5. **Frontend** consumes the API via `/lib/api.ts`. The sandbox page displays a choropleth map (Leaflet + OpenStreetMap), KPI cards, scenario sliders, ranked table, and drilldown drawer. The projects page lists projects with filters. Project detail shows comparables and memo generation.

## Key Interfaces

- **DataProvider**: `get_regions()`, `get_projects()`, `get_project()`, `get_region()`
- **VectorService**: `upsert_vectors()`, `query_similar()`
- **MemoClient**: `generate_memo(context: MemoContext) -> Memo`

## GeoJSON

`/geo/countries.geojson` and `apps/web/public/geo/countries.geojson` contain placeholder polygons with `region_id` in feature properties. Replace with a real `countries.geojson` where feature `id` or `properties.region_id` matches region IDs in the data.
