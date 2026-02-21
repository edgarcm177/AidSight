#!/usr/bin/env python3
"""
Run Aftershock preprocessing: build Sahel panel, spillover graph, features.

Outputs: dataml/data/processed/sahel_panel.parquet, spillover_graph.parquet, features.parquet.

Run from repo root: python -m dataml.scripts.run_preprocess
Or: python dataml/scripts/run_preprocess.py
"""

import logging
import sys
from pathlib import Path

# Ensure repo root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dataml.src.preprocess import main

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")

if __name__ == "__main__":
    main()
