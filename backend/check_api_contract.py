#!/usr/bin/env python3
"""
Lightweight API contract check: hits main HTTP endpoints and verifies response shape.
Uses FastAPI TestClient (no running server required). Run from repo root:
  python backend/check_api_contract.py
  # or: python -m backend.check_api_contract
Exits with 0 if all checks pass, 1 otherwise.
"""
import sys
from pathlib import Path

# Ensure repo root is on path
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from fastapi.testclient import TestClient
    from backend.main import app
except ImportError as e:
    print("FAIL: Could not import app.", e)
    sys.exit(1)

client = TestClient(app)
failed = []


def ok(name: str, cond: bool, msg: str = ""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {msg}" if msg else ""))
    if not cond:
        failed.append(name)


def main():
    print("API contract check (backend.main:app)\n")

    # GET /crises/
    r = client.get("/crises/")
    data = r.json() if r.status_code == 200 else []
    ok("GET /crises/", r.status_code == 200 and isinstance(data, list), f"status={r.status_code}" if r.status_code != 200 else "")
    ok("GET /crises/ non-empty", len(data) > 0, "list is empty" if len(data) == 0 else "")

    crisis_id = data[0]["id"] if data else None

    # POST /simulate/
    if crisis_id:
        payload = {
            "crisis_id": crisis_id,
            "funding_changes": [
                {"sector": "Health", "delta_usd": -500_000},
                {"sector": "WASH", "delta_usd": 0},
            ],
            "shock": {"inflation_pct": 0.0, "drought": False, "conflict_intensity": 0.0},
        }
        r = client.post("/simulate/", json=payload)
        sim = r.json() if r.status_code == 200 else {}
        ok("POST /simulate/", r.status_code == 200, f"status={r.status_code}")
        ok("POST /simulate/ TTC fields", "metrics" in sim and "baseline_ttc_days" in sim.get("metrics", {}))
        sim_result = sim
    else:
        ok("POST /simulate/", False, "no crisis_id")
        sim_result = {}

    # GET /twins/PRJ001
    r = client.get("/twins/PRJ001")
    twin = r.json() if r.status_code == 200 else {}
    ok("GET /twins/PRJ001", r.status_code == 200, f"status={r.status_code}")
    ok("GET /twins/ similarity_score", "similarity_score" in twin)

    # POST /memos/
    if crisis_id and sim_result:
        payload = {
            "crisis_id": crisis_id,
            "simulation": sim_result,
        }
        r = client.post("/memos/", json=payload)
        memo = r.json() if r.status_code == 200 else {}
        ok("POST /memos/", r.status_code == 200, f"status={r.status_code}")
        ok("POST /memos/ title, body, key_risks", all(k in memo for k in ("title", "body", "key_risks")))
    else:
        ok("POST /memos/", False, "skipped (no crisis or sim)")

    print()
    if failed:
        print(f"Summary: FAIL ({len(failed)} check(s) failed)")
        sys.exit(1)
    print("Summary: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
