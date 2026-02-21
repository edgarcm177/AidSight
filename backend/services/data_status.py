"""
Crisis data status helper for hackathon debugging.
Returns JSON-serializable summary of null rates and imputation.
"""

from typing import Any, Dict

import pandas as pd


def get_crisis_data_status(crises_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Return a tiny JSON-serializable dict with crisis data health metrics.

    Assumes caller has already loaded crises.parquet into a DataFrame.
    Does not load CSVs or Parquet files.
    """
    row_count = int(len(crises_df))

    key_cols = ["people_in_need", "funding_required", "funding_received", "coverage", "population"]
    null_rates: Dict[str, float] = {}
    for c in key_cols:
        if c in crises_df.columns:
            null_rates[c] = round(float(crises_df[c].isna().mean() * 100.0), 3)
        else:
            null_rates[c] = 100.0  # missing column treated as 100% null

    imputation_rates: Dict[str, float] = {}
    if "funding_missing" in crises_df.columns:
        imputation_rates["funding_received"] = round(
            float(crises_df["funding_missing"].mean() * 100.0), 3
        )
    if "population_missing" in crises_df.columns:
        imputation_rates["population"] = round(
            float(crises_df["population_missing"].mean() * 100.0), 3
        )

    return {
        "row_count": row_count,
        "null_rates": null_rates,
        "imputation_rates": imputation_rates,
    }
