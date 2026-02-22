#!/usr/bin/env python3
"""
Data & ML smoke test: Aftershock endpoints (POST /simulate/shock, GET /crises/*, GET /projects/*)
plus legacy AidSight flows (crises, projects, fragility simulate, memo, twins).

Run before hacking, after pulling, and before demos to confirm the backend stack is healthy.
Usage: python run_smoketest.py
"""
from backend.services.healthcheck import run_data_ml_smoketest, run_aftershock_smoketest

if __name__ == "__main__":
    print("--- Aftershock endpoints ---")
    r_aft = run_aftershock_smoketest()
    for k, v in r_aft.items():
        print(f"  {k}: {v}")

    print("\n--- Legacy AidSight flows ---")
    r_leg = run_data_ml_smoketest()
    for k, v in r_leg.items():
        print(f"  {k}: {v}")

    aft_ok = all(v for k, v in r_aft.items() if k.endswith("_ok"))
    leg_ok = (
        r_leg.get("crises_present")
        and r_leg.get("projects_present")
        and r_leg.get("simulate_ok")
        and r_leg.get("memo_ok")
        and r_leg.get("twins_ok")
    )
    print(f"\n  Aftershock: {'PASS' if aft_ok else 'FAIL'}")
    print(f"  Legacy: {'PASS' if leg_ok else 'FAIL'}")
    exit(0 if (aft_ok and leg_ok) else 1)
