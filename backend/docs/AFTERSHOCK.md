# Aftershock Simulation

Spillover simulation engine for funding adjustments and cross-border/regional effects over a short horizon (6–12 months / 1–2 steps).

## Endpoints

### GET /status

Returns baseline map/table data for frontend rendering.

**Response:** `StatusResponse`
- `baseline_year`: int
- `countries`: List of `CountryBaseline` (country, severity, funding_usd, displaced_in, displaced_out, risk_score)
- `edges`: List of `Edge` (src, dst, weight) for drawing spillover arrows
- `available_years`: List[int]
- `notes`: List[str]

### POST /simulate/aftershock

Runs spillover simulation given epicenter and funding change.

**Request:** `AftershockParams`
```json
{
  "epicenter": "BFA",
  "delta_funding_pct": -0.2,
  "horizon_steps": 2,
  "region_scope": null,
  "cost_per_person": 250,
  "debug": false
}
```

- `epicenter`: ISO3 or region_id (e.g. "BFA", "MLI")
- `delta_funding_pct`: -0.2 = cut 20%, +0.1 = add 10%. Clamped to [-0.3, 0.3].
- `horizon_steps`: 1 or 2 (clamped)
- `region_scope`: optional list of allowed countries
- `cost_per_person`: default 250 (for extra_cost_usd estimate)
- `debug`: if true, includes graph_edges_used in response

**Response:** `AftershockResult`
- `baseline_year`, `epicenter`, `delta_funding_pct`, `horizon_steps`
- `affected`: List of `AffectedCountryImpact` (country, delta_severity, delta_displaced, extra_cost_usd, prob_underfunded_next, explanation)
- `totals`: `TotalsImpact` (total_delta_displaced, total_extra_cost_usd, affected_countries, max_delta_severity)
- `graph_edges_used`: optional (only when debug=true)
- `notes`: List[str]

## Example curl

```bash
# Get status (baseline)
curl http://localhost:8000/status/

# Run aftershock simulation (20% funding cut at Burkina Faso)
curl -X POST http://localhost:8000/simulate/aftershock \
  -H "Content-Type: application/json" \
  -d '{"epicenter":"BFA","delta_funding_pct":-0.2,"horizon_steps":2}'
```

## Switching from mock to real data

1. Place `region_panel.parquet` in `backend/data/processed/` with columns: country (or iso3), year, severity, funding_usd, displaced_in, displaced_out, coverage_proxy (or coverage).
2. Place `graph.json` in `backend/models/` with format: `{"edges": [{"src": "BFA", "dst": "MLI", "weight": 0.4}, ...]}`.
3. Restart backend. If files exist, `FileAftershockDataProvider` uses them; otherwise falls back to mock with a log warning.

## Memo integration

`POST /memos/` accepts optional `aftershock` field (AftershockResult). When provided, the memo includes a spillover impact paragraph.

## Testing

From project root:
```bash
pytest backend/tests/test_aftershock.py -v
```
