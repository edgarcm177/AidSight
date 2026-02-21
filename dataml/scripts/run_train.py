#!/usr/bin/env python3
"""
Train Aftershock spillover model.

Requires: dataml/data/processed/sahel_panel.parquet, spillover_graph.parquet (run run_preprocess first).
Outputs: dataml/models/spillover_model.pt, model_config.json.

Run from repo root: python -m dataml.scripts.run_train
Or: python dataml/scripts/run_train.py
"""

import logging
import sys
from pathlib import Path

# Ensure repo root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dataml.src.train import train_model

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")

if __name__ == "__main__":
    train_model()
