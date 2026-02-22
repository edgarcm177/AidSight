"""Status endpoint for baseline map/table rendering. Uses DataML nodes/edges/baseline when available."""

from fastapi import APIRouter

from ..models import StatusResponse, CountryBaseline, Edge
from ..services.dataml_status_data import get_status_data

router = APIRouter()


@router.get("/", response_model=StatusResponse)
def get_status():
    """
    Baseline status for map/table: countries, edges, available years.
    Loads from DataML (nodes.json, edges.json, baseline_predictions.json) when present;
    otherwise falls back to backend mock data.
    """
    year, countries_raw, edges_raw, years, notes = get_status_data()

    countries = [
        CountryBaseline(
            country=c.get("country", ""),
            severity=c.get("severity", 0.5),
            funding_usd=c.get("funding_usd", 0),
            displaced_in=c.get("displaced_in", 0),
            displaced_out=c.get("displaced_out", 0),
            risk_score=c.get("risk_score"),
        )
        for c in countries_raw
    ]

    edges = [
        Edge(src=e.get("src", ""), dst=e.get("dst", ""), weight=e.get("weight", 0))
        for e in edges_raw
    ]

    return StatusResponse(
        baseline_year=year,
        countries=countries,
        edges=edges,
        available_years=years,
        notes=notes,
    )
