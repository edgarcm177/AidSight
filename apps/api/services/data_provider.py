"""Data provider interface and mock implementation."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from models import Project, RegionMetric


class DataProvider(ABC):
    """Abstract interface for loading regions and projects."""

    @abstractmethod
    def get_regions(self) -> List[RegionMetric]:
        pass

    @abstractmethod
    def get_projects(
        self,
        region_id: Optional[str] = None,
        flagged: Optional[bool] = None,
    ) -> List[Project]:
        pass

    @abstractmethod
    def get_project(self, project_id: str) -> Optional[Project]:
        pass

    @abstractmethod
    def get_region(self, region_id: str) -> Optional[RegionMetric]:
        pass


class MockDataProvider(DataProvider):
    """Loads mock data from JSON files."""

    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self._regions: Optional[List[RegionMetric]] = None
        self._projects: Optional[List[Project]] = None

    def _load_regions(self) -> List[RegionMetric]:
        if self._regions is not None:
            return self._regions
        import json

        path = self.data_path / "regions.json"
        if not path.exists():
            return []
        with open(path) as f:
            raw = json.load(f)
        self._regions = [RegionMetric(**r) for r in raw]
        return self._regions

    def _load_projects(self) -> List[Project]:
        if self._projects is not None:
            return self._projects
        import json

        path = self.data_path / "projects.json"
        if not path.exists():
            return []
        with open(path) as f:
            raw = json.load(f)
        self._projects = [Project(**p) for p in raw]
        return self._projects

    def get_regions(self) -> List[RegionMetric]:
        return self._load_regions()

    def get_projects(
        self,
        region_id: Optional[str] = None,
        flagged: Optional[bool] = None,
    ) -> List[Project]:
        projects = self._load_projects()
        if region_id is not None:
            projects = [p for p in projects if p.region_id == region_id]
        if flagged is not None:
            projects = [p for p in projects if (p.flagged or False) == flagged]
        return projects

    def get_project(self, project_id: str) -> Optional[Project]:
        for p in self._load_projects():
            if p.project_id == project_id:
                return p
        return None

    def get_region(self, region_id: str) -> Optional[RegionMetric]:
        for r in self._load_regions():
            if r.region_id == region_id:
                return r
        return None
