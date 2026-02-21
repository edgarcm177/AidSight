"""
Load preprocessed Parquet tables for AidSight.

Use load_crises() and load_projects() in FastAPI routers/services to get
DataFrames with the expected schemas for TTC/Equity calculations and Success Twin embeddings.
"""

from pathlib import Path

import pandas as pd

# Path to backend/data/ (directory containing crises.parquet, projects.parquet)
DATA_DIR = Path(__file__).resolve().parent


def load_crises() -> pd.DataFrame:
    """Load crises table. Run scripts/preprocess.py first if files are missing."""
    return pd.read_parquet(DATA_DIR / "crises.parquet")


def load_projects() -> pd.DataFrame:
    """Load projects table. Run scripts/preprocess.py first if files are missing."""
    return pd.read_parquet(DATA_DIR / "projects.parquet")
