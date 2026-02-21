"""Scenario stress-test engine with rebalance heuristic."""

from typing import List, Tuple

from models import RegionMetric, ScenarioParams, ScenarioResult, SuggestedAllocation


def run_stress_test(
    regions: List[RegionMetric],
    params: ScenarioParams,
) -> ScenarioResult:
    """Apply stress transforms and compute updated metrics + rebalance."""
    updated: List[RegionMetric] = []
    region_map = {r.region_id: r for r in regions}

    for r in regions:
        req = r.required_funding or (r.funding_gap + (r.funding_received or 0))
        funding_received = r.funding_received or (req * r.coverage_pct)
        monthly_burn = r.monthly_burn or (req / 12.0)

        # Stressed required funding
        req_stressed = req * (1 + params.inflation_shock) * (1 + params.climate_shock)

        # Effective funding after access shock + funding delta allocation
        # Initially we don't allocate funding_delta; rebalance does that
        delta_alloc = 0.0
        effective_funding = funding_received * (1 - params.access_shock) + delta_alloc

        coverage_stressed = effective_funding / req_stressed if req_stressed > 0 else 0.0
        runway_stressed = effective_funding / monthly_burn if monthly_burn > 0 else 0.0
        gap_stressed = max(0, req_stressed - effective_funding)
        risk_stressed = 1.0 - min(1.0, coverage_stressed)

        updated.append(
            RegionMetric(
                region_id=r.region_id,
                region_name=r.region_name,
                risk_score=max(0, min(1, risk_stressed)),
                coverage_pct=min(2.0, coverage_stressed),
                funding_gap=gap_stressed,
                volatility=r.volatility,
                runway_months=runway_stressed,
                coverage_pct_baseline=r.coverage_pct,
                coverage_pct_stressed=coverage_stressed,
                runway_months_baseline=r.runway_months,
                runway_months_stressed=runway_stressed,
                required_funding=req_stressed,
                funding_received=effective_funding,
                monthly_burn=monthly_burn,
            )
        )

    # Rebalance heuristic: allocate funding_delta to regions with highest marginal return
    suggested, regret = _rebalance(updated, params.funding_delta, region_map, params)

    # Top downside regions: lowest coverage_stressed
    sorted_by_downside = sorted(
        updated, key=lambda x: (x.coverage_pct_stressed or x.coverage_pct)
    )
    top_downside = [r.region_id for r in sorted_by_downside[:5]]

    return ScenarioResult(
        updated_region_metrics=updated,
        top_downside_regions=top_downside,
        suggested_allocations=suggested,
        regret_score=regret,
    )


def _rebalance(
    updated: List[RegionMetric],
    funding_delta: float,
    region_map: dict,
    params: ScenarioParams,
) -> Tuple[List[SuggestedAllocation], float]:
    """Simple heuristic: marginal_return = (1 - coverage) / required_funding, with diminishing returns."""
    if funding_delta <= 0:
        return [], 0.0

    # Current weighted coverage (by required funding)
    total_req = sum(r.required_funding or 0 for r in updated)
    if total_req <= 0:
        return [], 0.0

    current_weighted = sum(
        (r.coverage_pct_stressed or r.coverage_pct)
        * ((r.required_funding or 0) / total_req)
        for r in updated
    )

    # Allocate iteratively: each unit goes to region with highest marginal_return
    remaining = funding_delta
    step = funding_delta / 20  # coarse steps
    allocations: dict = {r.region_id: 0.0 for r in updated}
    working_funding = {
        r.region_id: r.funding_received or 0 for r in updated
    }

    while remaining > 0.001 and step > 0.0001:
        best_region = None
        best_margin = -1.0
        for r in updated:
            req = r.required_funding or 1.0
            cov = (working_funding[r.region_id] + allocations[r.region_id]) / req
            cov = min(1.0, cov)
            # Diminishing returns: marginal_return decreases as coverage increases
            marginal = (1 - cov) ** 1.5 / req if req > 0 else 0
            if marginal > best_margin:
                best_margin = marginal
                best_region = r.region_id

        if best_region is None:
            break

        add = min(step, remaining)
        allocations[best_region] += add
        remaining -= add

    suggested = [
        SuggestedAllocation(region_id=rid, delta_funding=round(d, 2))
        for rid, d in allocations.items()
        if d > 0.01
    ]

    # Simulate rebalanced weighted coverage
    total_effective_after = sum(
        (r.funding_received or 0) + allocations[r.region_id]
        for r in updated
    )
    total_req_stressed = sum(r.required_funding or 0 for r in updated)
    rebalanced_weighted = (
        total_effective_after / total_req_stressed if total_req_stressed > 0 else 0
    )

    # Regret: how much better could we have done?
    regret = max(0, rebalanced_weighted - current_weighted)

    return suggested, round(regret, 4)
