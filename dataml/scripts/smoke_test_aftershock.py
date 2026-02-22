#!/usr/bin/env python3
"""
Smoke test for DataML simulate_aftershock.
Runs simulation for each UI epicenter (BFA, MLI, NER, TCD) and checks outputs.
Run from repo root: python dataml/scripts/smoke_test_aftershock.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dataml.scripts._region_config import DEMO_EPICENTERS


def main() -> int:
    from dataml.src.simulate_aftershock import simulate_aftershock

    ok = 0
    for epicenter in DEMO_EPICENTERS:
        try:
            r = simulate_aftershock(
                node_iso3=epicenter,
                delta_funding_pct=-0.2,
                horizon_years=2,
            )
            displaced = r.get("total_extra_displaced", 0)
            affected = r.get("affected", [])
            n_aff = len(affected)
            if displaced > 0 and n_aff > 0:
                print(f"{epicenter}: extra_displaced={int(displaced):,}, affected={n_aff}")
                ok += 1
            else:
                print(f"{epicenter}: WARN displaced={displaced} affected={n_aff}")
        except Exception as e:
            print(f"{epicenter}: ERROR {e}")
    if ok == len(DEMO_EPICENTERS):
        print("Smoke test OK.")
        return 0
    print(f"Smoke test: {ok}/{len(DEMO_EPICENTERS)} passed.")
    return 1


if __name__ == "__main__":
    exit(main())
