"""Tests for Aftershock simulation endpoints."""

import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from backend.main import app

client = TestClient(app)


def test_get_status_returns_sane_structure():
    """GET /status returns 200 and expected structure."""
    r = client.get("/status/")
    assert r.status_code == 200
    j = r.json()
    assert "baseline_year" in j
    assert "countries" in j
    assert "edges" in j
    assert "available_years" in j
    assert isinstance(j["countries"], list)
    assert isinstance(j["edges"], list)
    assert len(j["countries"]) >= 1


def test_simulate_aftershock_deterministic():
    """POST /simulate/aftershock returns deterministic results."""
    payload = {"epicenter": "BFA", "delta_funding_pct": -0.2, "horizon_steps": 2}
    r1 = client.post("/simulate/aftershock", json=payload)
    r2 = client.post("/simulate/aftershock", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    j1 = r1.json()
    j2 = r2.json()
    assert j1["epicenter"] == "BFA"
    assert j1["affected"] == j2["affected"]
    assert j1["totals"]["total_delta_displaced"] == j2["totals"]["total_delta_displaced"]


def test_simulate_aftershock_clamping():
    """delta_funding_pct and horizon_steps are clamped."""
    r = client.post(
        "/simulate/aftershock",
        json={"epicenter": "BFA", "delta_funding_pct": 0.99, "horizon_steps": 10},
    )
    assert r.status_code == 200
    j = r.json()
    assert j["delta_funding_pct"] == 0.3
    assert j["horizon_steps"] == 2


def test_simulate_aftershock_invalid_epicenter():
    """Invalid epicenter returns 400."""
    r = client.post(
        "/simulate/aftershock",
        json={"epicenter": "XXX", "delta_funding_pct": -0.1},
    )
    assert r.status_code == 400
