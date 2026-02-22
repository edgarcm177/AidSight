from typing import List, Optional
from pydantic import BaseModel, computed_field


class Crisis(BaseModel):
    id: str
    name: str
    country: str
    region: Optional[str] = None
    severity: float
    people_in_need: int
    funding_required: float
    funding_received: float
    coverage: float  # 0–1
    time_to_collapse_days: Optional[float] = None
    equity_shift_pct: Optional[float] = None


class ScenarioShock(BaseModel):
    inflation_pct: float = 0.0
    drought: bool = False
    conflict_intensity: float = 0.0  # 0–1


class FundingChange(BaseModel):
    sector: str
    delta_usd: float


class ScenarioInput(BaseModel):
    crisis_id: str
    funding_changes: List[FundingChange]
    shock: ScenarioShock
    what_if_text: Optional[str] = None


class SimulationMetrics(BaseModel):
    baseline_ttc_days: float
    scenario_ttc_days: float
    baseline_equity_shift_pct: float
    scenario_equity_shift_pct: float
    at_risk_population: int


class RegionImpact(BaseModel):
    region: str
    delta_ttc_days: float
    funding_gap_usd: float


class SimulationResult(BaseModel):
    crisis_id: str
    metrics: SimulationMetrics
    impacted_regions: List[RegionImpact]


class Project(BaseModel):
    id: str
    name: str
    country: str
    year: int
    sector: str
    description: str


class TwinResult(BaseModel):
    target_project_id: str
    twin_project_id: str
    similarity_score: float
    bullets: List[str]
    twin_name: Optional[str] = None  # Human-readable label, e.g. "Health project AFG 2022"

    @computed_field
    @property
    def project_id(self) -> str:
        """Alias for twin_project_id for frontend compatibility."""
        return self.twin_project_id


class MemoRequest(BaseModel):
    crisis_id: Optional[str] = None
    scenario: Optional[ScenarioInput] = None
    simulation: Optional[SimulationResult] = None
    twin: Optional[TwinResult] = None
    aftershock: Optional["AftershockResult"] = None  # spillover context for memo


class MemoResponse(BaseModel):
    title: str
    body: str
    key_risks: List[str]

    @computed_field
    @property
    def memo(self) -> str:
        """Alias for body for frontend compatibility (SuccessTwinPanel expects memoResult.memo)."""
        return self.body


# --- Aftershock Simulation (DataML contract) ---


class SimulateRequest(BaseModel):
    """Request for DataML simulate_aftershock. Matches dataml contract."""
    country: str  # ISO3, e.g., "BFA"
    delta_funding_pct: float  # e.g., -0.2 for -20%
    horizon_steps: int = 2


class AffectedCountry(BaseModel):
    """Per-country impact from DataML simulate_aftershock."""
    country: str
    delta_severity: float
    delta_displaced: float  # numerical impact; can have decimal places
    extra_cost_usd: float
    prob_underfunded_next: float


class SimulateResponse(BaseModel):
    """Response from DataML simulate_aftershock. Pass-through schema."""
    baseline_year: int
    epicenter: str
    delta_funding_pct: float
    affected: list[AffectedCountry]
    total_extra_displaced: float  # numerical impact; can have decimal places
    total_extra_cost_usd: float
    notes: list[str]


# --- Aftershock (legacy/extended schema) ---


class AftershockParams(BaseModel):
    epicenter: str
    delta_funding_pct: float
    horizon_steps: int = 2
    region_scope: Optional[List[str]] = None
    cost_per_person: Optional[float] = 250.0
    debug: Optional[bool] = False


class AffectedCountryImpact(BaseModel):
    country: str
    delta_severity: float
    delta_displaced: float
    extra_cost_usd: float
    prob_underfunded_next: float
    explanation: Optional[str] = None
    projected_severity: Optional[float] = None  # 0-1 scale for X/10 display
    projected_coverage: Optional[float] = None  # 0-1; epicenter = baseline + funding change


class TotalsImpact(BaseModel):
    total_delta_displaced: float
    total_extra_cost_usd: float
    affected_countries: int
    max_delta_severity: float


class EdgeImpact(BaseModel):
    src: str
    dst: str
    weight: float
    propagated_displaced: float
    propagated_severity: float


class AftershockResult(BaseModel):
    baseline_year: int
    epicenter: str
    delta_funding_pct: float
    horizon_steps: int
    affected: List[AffectedCountryImpact]
    totals: TotalsImpact
    graph_edges_used: Optional[List[EdgeImpact]] = None
    notes: List[str] = []


class CountryBaseline(BaseModel):
    country: str
    severity: float
    funding_usd: float
    displaced_in: float
    displaced_out: float
    risk_score: Optional[float] = None


class Edge(BaseModel):
    src: str
    dst: str
    weight: float


class StatusResponse(BaseModel):
    baseline_year: int
    countries: List[CountryBaseline]
    edges: List[Edge]
    available_years: List[int]
    notes: List[str] = []


MemoRequest.model_rebuild()
