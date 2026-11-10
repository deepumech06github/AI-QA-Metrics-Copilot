"""Data structures for release metrics and evidence-backed insights."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ReleaseRecord:
    release_id: str
    release_date: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    blocked_tests: int
    automated_tests: int
    escaped_defects: int
    pre_release_defects: int
    production_incidents: int
    flaky_tests: int
    automation_duration_minutes: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReleaseMetrics:
    release_id: str
    release_date: str
    pass_rate: float
    automation_coverage: float
    blocked_rate: float
    defect_escape_rate: float
    flaky_rate: float
    escaped_defects: int
    production_incidents: int
    automation_duration_minutes: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MetricInsight:
    severity: str
    title: str
    evidence: str
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

