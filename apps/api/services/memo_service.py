"""Memo generation service with Sphinx AI client."""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict

from models import Memo, MemoContext

logger = logging.getLogger(__name__)


class MemoClient(ABC):
    """Abstract interface for memo generation."""

    @abstractmethod
    def generate_memo(self, context: MemoContext) -> Memo:
        pass


class FakeSphinxClient(MemoClient):
    """Deterministic placeholder memo generator."""

    def generate_memo(self, context: MemoContext) -> Memo:
        project = (context.project or {}).get("title", "Selected Project")
        scenario = context.scenario_params or {}
        inflation = scenario.get("inflation_shock", 0) * 100
        climate = scenario.get("climate_shock", 0) * 100

        return Memo(
            sections={
                "recommendation": f"Recommend APPROVE with conditions for {project}. "
                "Portfolio stress test suggests moderate resilience under baseline; "
                "implement contingency triggers for inflation above 15%.",
                "base_case": "Base case assumes no further shocks. Coverage remains stable "
                "at current levels with projected runways above 6 months in priority regions.",
                "downside_case": f"Downside: inflation shock of {inflation:.0f}% and climate "
                f"shock of {climate:.0f}% compress runways by ~20%. Some regions drop below "
                "4-month runway.",
                "severe_case": "Severe: combined shocks + access constraints. Portfolio-weighted "
                "coverage falls below 50%. Recommend pre-emptive reallocation to highest-gap regions.",
                "risks": "Key risks: unmodeled FX volatility, political access constraints, "
                "donor concentration, delayed disbursements.",
                "red_team": "Red team view: model understates tail risk. Real-world shocks "
                "are correlated; consider adding correlation stress. Cost-per-beneficiary "
                "comparisons may mask quality differences.",
                "evidence": "Evidence drawn from mock regional metrics and comparable project "
                "data. Replace with production pipeline outputs for IC use.",
            }
        )


class RealSphinxClient(MemoClient):
    """Skeleton for real Sphinx AI HTTP client."""

    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    def generate_memo(self, context: MemoContext) -> Memo:
        # TODO: POST context to Sphinx API, parse structured sections
        raise NotImplementedError("Sphinx client not implemented")


def get_memo_client() -> MemoClient:
    """Factory: use real client if env set, else fake."""
    endpoint = os.getenv("SPHINX_ENDPOINT", "").strip()
    api_key = os.getenv("SPHINX_API_KEY", "").strip()
    if endpoint and api_key:
        return RealSphinxClient(endpoint, api_key)
    logger.warning("SPHINX_ENDPOINT/SPHINX_API_KEY not set; using FakeSphinxClient")
    return FakeSphinxClient()
