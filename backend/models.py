from typing import List, Optional
from pydantic import BaseModel


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


class MemoRequest(BaseModel):
    crisis_id: Optional[str] = None
    scenario: Optional[ScenarioInput] = None
    simulation: Optional[SimulationResult] = None
    twin: Optional[TwinResult] = None


class MemoResponse(BaseModel):
    title: str
    body: str
    key_risks: List[str]
