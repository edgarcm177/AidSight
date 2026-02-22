# Aftershock Backend – Sphinx & DataML Integration

## Paths to Sphinx-Ready Tables (produced by DataML)

DataML writes these Parquet files under `dataml/data/processed/` for use with Actian Sphinx or other analytical tools:

| Table | Path | Description |
|-------|------|-------------|
| crises_for_sphinx | `dataml/data/processed/crises_for_sphinx.parquet` | Crisis-level metrics per (country_iso3, year): severity, funding_total_usd, needs_index, underfunding_score, chronic_underfunded_flag, extra_fields_json |
| projects_for_sphinx | `dataml/data/processed/projects_for_sphinx.parquet` | Project-level metrics: project_id, country_iso3, year, cluster, budget_usd, beneficiaries, ratio_reached, outlier_flag |
| aftershock_baseline_for_sphinx | `dataml/data/processed/aftershock_baseline_for_sphinx.parquet` | Baseline predictions per country: country_iso3, baseline_year, severity_pred_baseline, displacement_in_pred_baseline |

These files are read-only for the backend; do not modify them.

## Example Analytical Questions

- **"Why is crisis X more underfunded than its neighbors?"**  
  Join `crises_for_sphinx` with `edges.json` on country, compare `underfunding_score` and `chronic_underfunded_flag`.

- **"Which clusters have the most high-outlier projects by ratio_reached?"**  
  Query `projects_for_sphinx` filtered by `outlier_flag == 1`, group by `cluster`, aggregate by count or sum of `ratio_reached`.

- **"What is the baseline displacement prediction for country Y?"**  
  Query `aftershock_baseline_for_sphinx` for that `country_iso3`.

## Optional: Sphinx Preview Endpoint

A `/debug/sphinx_preview` endpoint can return the first 5 rows from each table as JSON for demos. Add it to the backend if needed.
