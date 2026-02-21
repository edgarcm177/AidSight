#!/usr/bin/env python3
"""
Data & ML smoke test: loads crises/projects, runs simulate/memo/twins in-process.

Run before hacking, after pulling, and before demos to confirm the backend stack is healthy.
Usage: python -m backend.run_smoketest  (from repo root)
"""
from .services.healthcheck import run_data_ml_smoketest

if __name__ == "__main__":
    r = run_data_ml_smoketest()
    for k, v in r.items():
        print(f"  {k}: {v}")
    all_ok = (
        r.get("crises_present")
        and r.get("projects_present")
        and r.get("simulate_ok")
        and r.get("memo_ok")
        and r.get("twins_ok")
    )
    print("\n  All *_ok flags True:", all_ok)
    exit(0 if all_ok else 1)
