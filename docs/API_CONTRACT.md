# AidSight API Contract

Base URL: `http://localhost:8000`

## Endpoints

### GET /health

**Response**
```json
{ "status": "ok", "app": "AidSight" }
```

---

### GET /regions

**Query params**
- `scenario_preset` (optional): `moderate` | `severe` — applies preset stress and returns stressed metrics

**Response:** Array of `RegionMetric`
```json
[
  {
    "region_id": "R1",
    "region_name": "Sahel Central",
    "risk_score": 0.72,
    "coverage_pct": 0.42,
    "funding_gap": 58000000,
    "volatility": 0.18,
    "runway_months": 4.2,
    "coverage_pct_baseline": null,
    "coverage_pct_stressed": null,
    "runway_months_baseline": null,
    "runway_months_stressed": null,
    "required_funding": 100000000,
    "funding_received": 42000000,
    "monthly_burn": 8333333
  }
]
```

---

### GET /regions/{region_id}

**Response**
```json
{
  "region": { /* RegionMetric */ },
  "projects": [ /* Project[] */ ]
}
```

---

### POST /scenario/run

**Request body:** `ScenarioParams`
```json
{
  "inflation_shock": 0.1,
  "climate_shock": 0.05,
  "access_shock": 0.1,
  "funding_delta": 5000000,
  "constraints": null
}
```

**Response:** `ScenarioResult`
```json
{
  "updated_region_metrics": [ /* RegionMetric[] */ ],
  "top_downside_regions": ["R10", "R7", "R3", "R4", "R1"],
  "suggested_allocations": [
    { "region_id": "R10", "delta_funding": 2500000 },
    { "region_id": "R7", "delta_funding": 1500000 }
  ],
  "regret_score": 0.042
}
```

---

### GET /projects

**Query params**
- `region_id` (optional): filter by region
- `flagged` (optional): `true` | `false`

**Response:** Array of `Project`
```json
[
  {
    "project_id": "P1",
    "title": "Sahel Nutrition Emergency Response",
    "description": "Integrated nutrition and health support...",
    "region_id": "R1",
    "sector": "Health",
    "budget": 4500000,
    "beneficiaries": 120000,
    "cost_per_beneficiary": 37.5,
    "flagged": false
  }
]
```

---

### GET /projects/{project_id}

**Response:** `Project`

---

### POST /projects/{project_id}/comparables

**Query params**
- `top_k` (optional, default 5): number of similar projects to return

**Response:** Array of `ComparableTrade`
```json
[
  {
    "project_id": "P5",
    "title": "Yemen Cholera Response",
    "similarity": 0.87,
    "key_reasons": [
      "Similar sector: Health",
      "Comparable budget: $5,200,000",
      "Serves 150,000 beneficiaries"
    ],
    "peer_metrics_summary": { "budget": 5200000, "beneficiaries": 150000 }
  }
]
```

---

### POST /memo/generate

**Request body:** `MemoContext`
```json
{
  "scenario_params": { "inflation_shock": 0.1, "climate_shock": 0.05, ... },
  "project": { /* Project */ },
  "comparables": [ /* ComparableTrade[] */ ],
  "region_metrics": [ /* RegionMetric[] */ ]
}
```

**Response:** `Memo`
```json
{
  "sections": {
    "recommendation": "...",
    "base_case": "...",
    "downside_case": "...",
    "severe_case": "...",
    "risks": "...",
    "red_team": "...",
    "evidence": "..."
  }
}
```
