"""
Read-only Databricks client for crisis_metrics.
Uses DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_HTTP_PATH.
If any required env var is missing, raises DatabricksDisabled immediately.
On SQL failure, logs and re-raises DatabricksDisabled so callers can fall back.
"""

import logging
import os

DatabricksDisabled = type("DatabricksDisabled", (Exception,), {})

logger = logging.getLogger(__name__)

# Table: aftershock.crisis_metrics
# Schema: country_iso3, year, severity_score, requirements_usd, funding_usd,
#         coverage_pct, pooled_fund_coverage_usd, underfunding_score
CRISIS_METRICS_SQL = """
SELECT
  country_iso3,
  year,
  severity_score,
  requirements_usd,
  funding_usd,
  coverage_pct,
  pooled_fund_coverage_usd,
  underfunding_score
FROM aftershock.crisis_metrics
LIMIT {limit}
"""


def _is_configured() -> bool:
    host = os.environ.get("DATABRICKS_HOST", "").strip()
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    path = os.environ.get("DATABRICKS_HTTP_PATH", "").strip()
    return bool(host and token and path)


def fetch_crisis_metrics(limit: int = 500) -> list[dict]:
    """
    Returns rows from crisis_metrics table in Databricks.
    Schema: country_iso3, year, severity_score, requirements_usd,
    funding_usd, coverage_pct, pooled_fund_coverage_usd, underfunding_score
    """
    if not _is_configured():
        raise DatabricksDisabled("Databricks env vars (DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_HTTP_PATH) not set")

    try:
        from databricks import sql
    except ImportError:
        raise DatabricksDisabled("databricks-sql-connector not installed; pip install databricks-sql-connector")

    host = os.environ["DATABRICKS_HOST"].strip().replace("https://", "")
    token = os.environ["DATABRICKS_TOKEN"].strip()
    path = os.environ["DATABRICKS_HTTP_PATH"].strip()

    conn = None
    try:
        conn = sql.connect(server_hostname=host, http_path=path, access_token=token)
        cur = conn.cursor()
        q = CRISIS_METRICS_SQL.format(limit=limit)
        cur.execute(q)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        logger.warning("Databricks fetch_crisis_metrics failed: %s", e)
        raise DatabricksDisabled(f"Databricks SQL failed: {e}") from e
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
