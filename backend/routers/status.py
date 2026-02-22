"""Status endpoint for baseline map/table rendering."""

from fastapi import APIRouter

from ..models import StatusResponse, CountryBaseline, Edge
from ..services.aftershock_data import get_aftershock_provider

router = APIRouter()

_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        _provider = get_aftershock_provider()
    return _provider


@router.get("/", response_model=StatusResponse)
def get_status():
    """
    Baseline status for map/table: countries, edges, available years.
    Used by frontend to render baseline view.
    """
    provider = _get_provider()
    year = provider.get_baseline_year()
    panel = provider.get_country_panel(year)
    edges_raw = provider.get_edges()
    years = provider.get_available_years()

    countries: list = []
    for iso3, row in panel.items():
        sev = row.get("severity", 0.5)
        cov = row.get("coverage_proxy", 0.5)
        risk_score = (1 - cov) * sev
        countries.append(
            CountryBaseline(
                country=iso3,
                severity=round(sev, 4),
                funding_usd=float(row.get("funding_usd", 0)),
                displaced_in=float(row.get("displaced_in", 0)),
                displaced_out=float(row.get("displaced_out", 0)),
                risk_score=round(risk_score, 4),
            )
        )

    edges = [
        Edge(src=str(e.get("src", "")), dst=str(e.get("dst", "")), weight=float(e.get("weight", 0)))
        for e in edges_raw
    ]

    notes = getattr(provider, "_notes", []) if hasattr(provider, "_notes") else []

    return StatusResponse(
        baseline_year=year,
        countries=countries,
        edges=edges,
        available_years=years,
        notes=notes,
    )
