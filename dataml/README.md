# Aftershock Data/ML Package

Data processing, spillover modeling, and export pipelines for the Aftershock humanitarian crisis forecasting project.

## Crisis Tables

| File | Description |
|------|-------------|
| **sahel_panel.parquet** | Country-year panel with crisis metrics: `country_iso3`, `year`, `severity`, `funding_total_usd`, `needs_index`, `underfunding_score`, `chronic_underfunded_flag`, `people_in_need`, `coverage`, etc. |
| **nodes.json** | Latest-year nodes for frontend: `country`, `year`, `severity`, `funding_total_usd`, `beneficiaries_total`, `funding_per_beneficiary`, `underfunding_score`, `chronic_underfunded_flag`. |
| **crises_for_sphinx.parquet** | Clean flat table for Sphinx/Databricks: `country_iso3`, `year`, `severity`, `funding_total_usd`, `needs_index`, `underfunding_score`, `chronic_underfunded_flag`, `extra_fields_json`. Used for "why is this crisis overlooked?" reasoning. |

## Project Tables

| File | Description |
|------|-------------|
| **project_metrics.parquet** | Project-level metrics: `project_id`, `country_iso3`, `year`, `cluster`, `budget_usd`, `beneficiaries`, `ratio_reached`, `outlier_flag`. |
| **project_neighbors.parquet** | KNN neighbors per project: `project_id`, `neighbor_id`, `similarity_score`, `neighbor_ratio_reached`. |
| **projects_for_sphinx.parquet** | Flat table for Sphinx: `project_id`, `country_iso3`, `year`, `cluster`, `budget_usd`, `beneficiaries`, `ratio_reached`, `outlier_flag`. |

## Embeddings (Actian VectorAI)

| File | Description |
|------|-------------|
| **crisis_embeddings.parquet** | Crisis embeddings for vector search. Columns: `country_iso3`, `year`, `severity`, `underfunding_score`, `chronic_underfunded_flag`, `description`, `embedding` (list of floats). **Actian ingestion**: Use `country_iso3` + `year` as composite ID, `embedding` as vector, other columns as metadata. |
| **project_embeddings.parquet** | Project embeddings for vector search. Columns: `project_id`, `country_iso3`, `year`, `cluster`, `ratio_reached`, `outlier_flag`, `description`, `embedding` (list of floats). **Actian ingestion**: Use `project_id` as ID, `embedding` as vector, other columns as metadata. |

### Suggested Backend Endpoints

- **`/similar_crises`** – Backed by `crisis_embeddings.parquet`. Accept `country_iso3`, `year` (or embedding vector), return top-k similar crises by cosine similarity on `embedding`.
- **`/similar_projects`** – Backed by `project_embeddings.parquet`. Accept `project_id` (or embedding vector), return top-k similar projects by cosine similarity on `embedding`.

## Scripts

| Script | Purpose |
|--------|---------|
| `run_preprocess` | Build sahel_panel, spillover_graph, features. |
| `run_train` | Train spillover GNN, save model + config. |
| `run_aftershock_smoketest` | Preprocess → train → simulate_aftershock("BFA", -0.2, 2), assert schema. |
| `export_baseline_structures` | Export nodes.json, edges.json, baseline_predictions.json. |
| `export_project_benchmarking` | Build projects, metrics, neighbors; export project_metrics.json, project_neighbors.json. |
| `export_sphinx_tables` | Build crisis/project embeddings; export crises_for_sphinx, projects_for_sphinx, aftershock_baseline_for_sphinx. |

Run from repo root: `python -m dataml.scripts.<script_name>`
