"""Pydantic models for AidSight API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RegionMetric(BaseModel):
    region_id: str
    region_name: str
    risk_score: float = Field(ge=0, le=1)
    coverage_pct: float = Field(ge=0, le=2)
    funding_gap: float
    volatility: float = Field(ge=0)
    runway_months: float = Field(ge=0)
    # baseline vs stressed (optional)
    coverage_pct_baseline: Optional[float] = None
    coverage_pct_stressed: Optional[float] = None
    runway_months_baseline: Optional[float] = None
    runway_months_stressed: Optional[float] = None
    required_funding: Optional[float] = None
    funding_received: Optional[float] = None
    monthly_burn: Optional[float] = None


class ScenarioConstraints(BaseModel):
    min_coverage_pct: Optional[float] = None
    max_allocation_per_region: Optional[float] = None
    priority_regions: Optional[List[str]] = None


class ScenarioParams(BaseModel):
    inflation_shock: float = Field(default=0.0, ge=0, le=2)
    climate_shock: float = Field(default=0.0, ge=0, le=2)
    access_shock: float = Field(default=0.0, ge=0, le=1)
    funding_delta: float = Field(default=0.0)
    constraints: Optional[ScenarioConstraints] = None


class SuggestedAllocation(BaseModel):
    region_id: str
    delta_funding: float


class ScenarioResult(BaseModel):
    updated_region_metrics: List[RegionMetric]
    top_downside_regions: List[str]
    suggested_allocations: List[SuggestedAllocation]
    regret_score: float


class Project(BaseModel):
    project_id: str
    title: str
    description: str
    region_id: str
    sector: str
    budget: float
    beneficiaries: int
    cost_per_beneficiary: Optional[float] = None
    flagged: Optional[bool] = False


class ComparableTrade(BaseModel):
    project_id: str
    title: str
    similarity: float
    key_reasons: List[str]
    peer_metrics_summary: Optional[Dict[str, Any]] = None


class Memo(BaseModel):
    sections: Dict[str, str] = Field(
        default_factory=lambda: {
            "recommendation": "",
            "base_case": "",
            "downside_case": "",
            "severe_case": "",
            "risks": "",
            "red_team": "",
            "evidence": "",
        }
    )


class MemoContext(BaseModel):
    scenario_params: Optional[Dict[str, Any]] = None
    project: Optional[Dict[str, Any]] = None
    comparables: Optional[List[Dict[str, Any]]] = None
    region_metrics: Optional[List[Dict[str, Any]]] = None
