# Data sources for AidSight

Where the app’s data comes from and how to get more (crises and projects).

---

## Current sources

### Crises (spillover, severity, funding)

| Source | Path | Used by | Notes |
|--------|------|--------|--------|
| **misfit_final_analysis.csv** | `backend/data/raw/` or `dataml/data/raw/` | `backend/scripts/preprocess.py` → `crises.parquet` | HNO/HRP-style: `code`, `Country_ISO3`, `years`, `In_Need`, `Population`, `origRequirements`, `revisedRequirements`, `funding_per_capita`, `Description`. Preprocess looks in backend raw first, then dataml raw. |

Required columns (or equivalents): country (ISO3), year, people in need, funding required/received (or requirements + funding per capita), description/name. Output: `backend/data/crises.parquet` (id, name, country, region, severity, people_in_need, funding_required, funding_received, coverage, year, …).

### Projects (Success Twin, similar projects, VectorAI)

| Source | Path | Used by | Notes |
|--------|------|--------|--------|
| **projects_sample.csv** (optional) | `backend/data/raw/` or `dataml/data/raw/` | `backend/scripts/preprocess.py` → `projects.parquet` | Columns: `id`, `name`, `country`, `year`, `sector`, `description`, `budget`, `beneficiaries` (optional: `cost_per_beneficiary`, `region`). |
| **cbpf_projects.csv** (optional) | `dataml/data/raw/` | Same preprocess | CBPF-style: `ProjectCode`, `CountryISO3`, `AllocationYear`, `Cluster`, `Budget`, `PeopleTargeted`. Used only if `projects_sample.csv` is absent. Gives one “project” per country-year allocation. |
| **Synthetic** | — | Same preprocess | If neither CSV exists: ~80 synthetic projects (epicenter countries + others) with region. |

Precedence: **projects_sample.csv** → **cbpf_projects.csv** → **synthetic**. Output: `backend/data/projects.parquet`.

### DataML (aftershock, embeddings, Sphinx)

| Source | Path | Used by |
|--------|------|--------|
| **misfit_final_analysis.csv** | `dataml/data/raw/` | Sahel panel, severity/funding stubs |
| **AllocationsByOrgType__*.csv** | `dataml/data/raw/` | `fetch_cbpf.py` → country_year_funding.csv |
| **202601_INFORM_Severity_*.xlsx** | `dataml/data/raw/` | `fetch_inform_severity.py` → country_year_severity.csv |
| **global-iom-dtm-*.csv** | `dataml/data/raw/` | `fetch_displacement_flows.py` → flow_edges.csv |
| **sahel_panel.parquet**, **spillover_graph.parquet** | `dataml/data/processed/` | Aftershock simulation, embeddings |

See `dataml/README.md` and the fetch scripts in `dataml/scripts/` for details.

---

## Getting more data

### More crises (country–year panel)

- **OCHA FTS (Financial Tracking Service)**  
  - https://fts.unocha.org  
  - Export or API: funding by appeal/country/year. Map to: country (ISO3), year, funding_required, funding_received (and optionally people_in_need from another source).

- **Humanitarian Response / Humanitarian Program Cycle (HRP/HNO)**  
  - OCHA’s Humanitarian Response plans and needs overviews.  
  - Often include: country, year, requirements, people in need, funded amounts. Can be merged with FTS for coverage.

- **INFORM Severity Index**  
  - https://drmkc.jrc.ec.europa.eu/inform-index  
  - `dataml/scripts/fetch_inform_severity.py` expects an Excel export in `dataml/data/raw/` (e.g. `202601_INFORM_Severity_-_January_2026.xlsx`). Use for severity by country (and optionally year).

- **Your own “misfit” CSV**  
  - One row per crisis (e.g. country–year). Columns as in “Current sources” above.  
  - Put the file in `backend/data/raw/misfit_final_analysis.csv` (or `dataml/data/raw/`).  
  - Run: `python -m backend.scripts.preprocess` to regenerate `backend/data/crises.parquet`.

### More projects (for Success Twin and similar projects)

- **projects_sample.csv (recommended)**  
  - One row per project. Columns: `id`, `name`, `country` (ISO3), `year`, `sector`, `description`, `budget`, `beneficiaries`. Optional: `region`, `cost_per_beneficiary`.  
  - Place in `backend/data/raw/projects_sample.csv` (or `dataml/data/raw/`).  
  - Preprocess will use it and add `region` from `COUNTRY_TO_REGION` if missing.

- **CBPF allocations**  
  - Country–year allocation tables (e.g. `ProjectCode`, `CountryISO3`, `AllocationYear`, `Cluster`, `Budget`, `PeopleTargeted`).  
  - Save as `dataml/data/raw/cbpf_projects.csv`. Used only when `projects_sample.csv` is not present; gives one project per country–year row.

- **OCHA FTS project-level**  
  - FTS can export funding by project/organization. Map: project id, country, year, sector/cluster, budget (and beneficiaries if available) into the same schema as `projects_sample.csv`.

- **Other humanitarian project datasets**  
  - Any CSV with project id, country, year, sector, budget, beneficiaries (and optional description) can be renamed/mapped to `projects_sample.csv` and placed in `backend/data/raw/` or `dataml/data/raw/`.

After adding or changing CSVs, run:

```bash
python -m backend.scripts.preprocess
```

Then restart the backend (and, if you use VectorAI, re-run the ingestion script so similar projects use the new data).

---

## Paths summary

- **Backend reads raw from (in order):**  
  `backend/data/raw/` then `dataml/data/raw/` for `misfit_final_analysis.csv` and `projects_sample.csv`.  
  So a single copy in `dataml/data/raw/` is enough.

- **Outputs:**  
  - `backend/data/crises.parquet`  
  - `backend/data/projects.parquet`  
  - DataML uses `dataml/data/processed/` for panel, graph, embeddings, etc.

- **Region:**  
  Crises and projects get a `region` (e.g. Sahel, East Africa) from the `COUNTRY_TO_REGION` map in `backend/scripts/preprocess.py` when not provided in the CSV.
