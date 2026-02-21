#!/usr/bin/env python3
"""
Aftershock Data/ML smoketest: preprocess, train, simulate_aftershock.

Verifies the full pipeline and simulate_aftershock output shape.
Run from repo root: python -m dataml.scripts.run_aftershock_smoketest
Or: python dataml/scripts/run_aftershock_smoketest.py
"""

import sys
from pathlib import Path

# Ensure repo root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    results = {}

    # 1. Preprocess
    try:
        from dataml.src.preprocess import main as preprocess_main
        preprocess_main()
        results["preprocess_ok"] = True
    except Exception as e:
        results["preprocess_ok"] = False
        results["preprocess_error"] = str(e)

    # 2. Train
    try:
        from dataml.src.train import train_model
        train_model()
        results["train_ok"] = True
    except Exception as e:
        results["train_ok"] = False
        results["train_error"] = str(e)

    # 3. simulate_aftershock
    try:
        from dataml.src.simulate_aftershock import simulate_aftershock
        out = simulate_aftershock("MLI", -10.0, 3)
        required = {"node_iso3", "delta_funding_pct", "horizon_years", "baseline", "scenario", "spillover_impacts", "trajectory"}
        has_all = all(k in out for k in required)
        assert has_all, f"Missing keys: {required - set(out.keys())}"
        assert out["baseline"].keys() >= {"coverage", "people_in_need", "funding_gap_usd"}
        assert out["scenario"].keys() >= {"coverage", "people_in_need", "funding_gap_usd"}
        assert isinstance(out["spillover_impacts"], list)
        assert isinstance(out["trajectory"], list)
        assert len(out["trajectory"]) == 4  # year_offset 0,1,2,3
        results["simulate_ok"] = True
    except Exception as e:
        results["simulate_ok"] = False
        results["simulate_error"] = str(e)

    for k, v in results.items():
        if k.endswith("_ok"):
            print(f"  {k}: {v}")
    all_ok = results.get("preprocess_ok", False) and results.get("train_ok", False) and results.get("simulate_ok", False)
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
