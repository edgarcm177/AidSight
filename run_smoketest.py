#!/usr/bin/env python3
"""Run the Data & ML smoke test. Usage: python run_smoketest.py"""
from backend.services.healthcheck import run_data_ml_smoketest

if __name__ == "__main__":
    r = run_data_ml_smoketest()
    for k, v in r.items():
        print(f"  {k}: {v}")
    all_ok = r.get("crises_present") and r.get("projects_present") and r.get("simulate_ok") and r.get("memo_ok") and r.get("twins_ok")
    print("\n  All *_ok flags True:", all_ok)
