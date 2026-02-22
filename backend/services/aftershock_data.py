"""
Aftershock data seam: interface + mock and file-based providers.
Swap mock for real by placing region_panel.parquet and graph.json at expected paths.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Paths for real data (fall back to mock if missing)
DATA_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = DATA_ROOT / "data" / "processed"
MODELS_DIR = DATA_ROOT / "models"
MOCK_DIR = DATA_ROOT / "mock_data"
PANEL_PARQUET = PROCESSED_DIR / "region_panel.parquet"
GRAPH_JSON = MODELS_DIR / "graph.json"


class AftershockDataProvider(ABC):
    """Interface for aftershock simulation baseline data."""

    @abstractmethod
    def get_baseline_year(self) -> int:
        pass

    @abstractmethod
    def get_country_panel(self, year: int) -> Dict[str, Dict[str, Any]]:
        """Return dict keyed by iso3 with baseline metrics."""
        pass

    @abstractmethod
    def get_edges(self) -> List[Dict[str, Any]]:
        """Return list of {src, dst, weight}."""
        pass

    @abstractmethod
    def get_available_years(self) -> List[int]:
        pass


class MockAftershockDataProvider(AftershockDataProvider):
    """Load from mock JSON files."""

    def __init__(self) -> None:
        self._panel: Dict[str, Any] = {}
        self._graph: Dict[str, Any] = {"edges": []}
        self._load()

    def _load(self) -> None:
        panel_path = MOCK_DIR / "aftershock_panel.json"
        graph_path = MOCK_DIR / "aftershock_graph.json"
        if panel_path.exists():
            with open(panel_path) as f:
                self._panel = json.load(f)
        if graph_path.exists():
            with open(graph_path) as f:
                self._graph = json.load(f)

    def get_baseline_year(self) -> int:
        return self._panel.get("baseline_year", 2025)

    def get_country_panel(self, year: int) -> Dict[str, Dict[str, Any]]:
        return self._panel.get("countries", {})

    def get_edges(self) -> List[Dict[str, Any]]:
        return self._graph.get("edges", [])

    def get_available_years(self) -> List[int]:
        return [self.get_baseline_year()]


class FileAftershockDataProvider(AftershockDataProvider):
    """Load from parquet + graph.json if they exist; else fall back to mock."""

    def __init__(self) -> None:
        self._mock = MockAftershockDataProvider()
        self._panel_df = None
        self._edges: List[Dict[str, Any]] = []
        self._use_real = False
        self._notes: List[str] = []  # for StatusResponse.notes

        if PANEL_PARQUET.exists() and GRAPH_JSON.exists():
            try:
                import pandas as pd
                self._panel_df = pd.read_parquet(PANEL_PARQUET)
                with open(GRAPH_JSON) as f:
                    data = json.load(f)
                self._edges = data.get("edges", [])
                self._use_real = True
                self._notes.append("Using real data: region_panel.parquet and graph.json")
            except Exception as e:
                logger.warning("Failed to load real aftershock data: %s; falling back to mock", e)
                self._notes.append(f"Fallback to mock: {e}")
        else:
            logger.warning(
                "Aftershock: region_panel.parquet or graph.json not found; using mock"
            )
            self._notes.append(
                "Using mock data. Place region_panel.parquet in data/processed/ "
                "and graph.json in models/ to use real data."
            )

    def get_baseline_year(self) -> int:
        if self._use_real and self._panel_df is not None and "year" in self._panel_df.columns:
            return int(self._panel_df["year"].iloc[0])
        return self._mock.get_baseline_year()

    def get_country_panel(self, year: int) -> Dict[str, Dict[str, Any]]:
        if self._use_real and self._panel_df is not None:
            df = self._panel_df
            if "year" in df.columns:
                df = df[df["year"] == year]
            result: Dict[str, Dict[str, Any]] = {}
            for _, row in df.iterrows():
                iso3 = str(row.get("country", row.get("iso3", "UNK")))
                result[iso3] = {
                    "country": iso3,
                    "severity": float(row.get("severity", 0.5)),
                    "funding_usd": float(row.get("funding_usd", row.get("funding", 0))),
                    "displaced_in": float(row.get("displaced_in", 0)),
                    "displaced_out": float(row.get("displaced_out", 0)),
                    "coverage_proxy": float(row.get("coverage_proxy", row.get("coverage", 0.5))),
                }
            return result
        return self._mock.get_country_panel(year)

    def get_edges(self) -> List[Dict[str, Any]]:
        if self._use_real and self._edges:
            return self._edges
        return self._mock.get_edges()

    def get_available_years(self) -> List[int]:
        if self._use_real and self._panel_df is not None and "year" in self._panel_df.columns:
            return sorted(self._panel_df["year"].unique().tolist())
        return self._mock.get_available_years()


def get_aftershock_provider() -> AftershockDataProvider:
    """Factory: use FileAftershockDataProvider (falls back to mock when real files missing)."""
    return FileAftershockDataProvider()
