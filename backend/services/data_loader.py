from pathlib import Path
from typing import Tuple

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent


def load_crises() -> pd.DataFrame:
    path = DATA_DIR / "crises.parquet"
    df = pd.read_parquet(path)
    return df


def load_projects() -> pd.DataFrame:
    path = DATA_DIR / "projects.parquet"
    df = pd.read_parquet(path)
    return df


def load_all() -> Tuple[pd.DataFrame, pd.DataFrame]:
    return load_crises(), load_projects()
