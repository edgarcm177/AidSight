#!/usr/bin/env python3
"""
Aftershock Data/ML smoketest: preprocess, train, simulate_aftershock.

Verifies the full pipeline and that simulate_aftershock returns the API schema
(baseline_year, epicenter, delta_funding_pct, affected, total_extra_displaced,
total_extra_cost_usd, notes). All paths use dataml-internal DATAML_ROOT.
Run from repo root: python -m dataml.scripts.run_aftershock_smoketest
Or: python dataml/scripts/run_aftershock_smoketest.py
"""

import json
import sys
from pathlib import Path

# Ensure repo root is on path so "dataml" package resolves
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

REQUIRED_KEYS = {
    "baseline_year",
    "epicenter",
    "delta_funding_pct",
    "affected",
    "total_extra_displaced",
    "total_extra_cost_usd",
}


def main() -> int:
    results = {}

    # 1. Preprocess (writes dataml/data/processed/*.parquet)
    try:
        from dataml.src.preprocess import main as preprocess_main
        preprocess_main()
        results["preprocess_ok"] = True
    except Exception as e:
        results["preprocess_ok"] = False
        results["preprocess_error"] = str(e)

    # 2. Train (writes dataml/models/spillover_model.pt, model_config.json)
    try:
        from dataml.src.train import train_model
        train_model()
        results["train_ok"] = True
    except Exception as e:
        results["train_ok"] = False
        results["train_error"] = str(e)

    # 3. simulate_aftershock: one example (BFA, -0.2, 2), pretty-print, assert schema
    try:
        from dataml.src.simulate_aftershock import simulate_aftershock
        out = simulate_aftershock("BFA", -0.2, 2)
        missing = REQUIRED_KEYS - set(out.keys())
        assert not missing, f"Missing keys: {missing}"
        assert isinstance(out["affected"], list)
        for entry in out["affected"]:
            assert "country" in entry and "delta_severity" in entry
            assert "delta_displaced" in entry and "extra_cost_usd" in entry
            assert "prob_underfunded_next" in entry
        print("\n--- simulate_aftershock(\"BFA\", -0.2, 2) response ---\n")
        print(json.dumps(out, indent=2))
        print()
        results["simulate_ok"] = True
    except Exception as e:
        results["simulate_ok"] = False
        results["simulate_error"] = str(e)

    for k, v in results.items():
        if k.endswith("_ok"):
            print(f"  {k}: {v}")
    all_ok = (
        results.get("preprocess_ok", False)
        and results.get("train_ok", False)
        and results.get("simulate_ok", False)
    )
    print("\n  All Aftershock *_ok flags True:", all_ok)
    if not all_ok and "preprocess_error" in results:
        print("  preprocess_error:", results["preprocess_error"])
    if not all_ok and "train_error" in results:
        print("  train_error:", results["train_error"])
    if not all_ok and "simulate_error" in results:
        print("  simulate_error:", results["simulate_error"])
    return 0 if all_ok else 1


if __name__ == "__main__":
    exit(main())
