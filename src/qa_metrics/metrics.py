"""CSV ingestion, metric calculations, and explainable trend signals."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from .models import MetricInsight, ReleaseMetrics, ReleaseRecord


REQUIRED_COLUMNS = {
    "release_id", "release_date", "total_tests", "passed_tests", "failed_tests", "blocked_tests",
    "automated_tests", "escaped_defects", "pre_release_defects", "production_incidents",
    "flaky_tests", "automation_duration_minutes",
}
COUNT_COLUMNS = {
    "total_tests", "passed_tests", "failed_tests", "blocked_tests", "automated_tests",
    "escaped_defects", "pre_release_defects", "production_incidents", "flaky_tests",
}


@dataclass(frozen=True)
class MetricThresholds:
    min_pass_rate: float = 0.95
    min_automation_coverage: float = 0.75
    max_blocked_rate: float = 0.10
    max_defect_escape_rate: float = 0.15
    max_flaky_rate: float = 0.05
    max_duration_growth_pct: float = 20.0


def parse_release_csv(text: str) -> list[ReleaseRecord]:
    """Parse and validate a release metrics CSV file."""

    if not text.strip():
        raise ValueError("The CSV is empty.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("The CSV needs a header row.")
    missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
    if missing:
        raise ValueError("Missing required CSV columns: " + ", ".join(missing))
    records = []
    seen = set()
    for row_number, row in enumerate(reader, start=2):
        try:
            release_id = (row.get("release_id") or "").strip()
            release_date = date.fromisoformat((row.get("release_date") or "").strip()).isoformat()
            if not release_id:
                raise ValueError("release_id cannot be blank")
            if release_id in seen:
                raise ValueError(f"duplicate release_id `{release_id}`")
            seen.add(release_id)
            counts = {name: int(row[name]) for name in COUNT_COLUMNS}
            duration = float(row["automation_duration_minutes"])
            if any(value < 0 for value in counts.values()) or duration < 0:
                raise ValueError("counts and durations must be non-negative")
            if counts["total_tests"] == 0:
                raise ValueError("total_tests must be greater than zero")
            if counts["passed_tests"] + counts["failed_tests"] + counts["blocked_tests"] > counts["total_tests"]:
                raise ValueError("passed + failed + blocked cannot exceed total_tests")
            if counts["automated_tests"] > counts["total_tests"]:
                raise ValueError("automated_tests cannot exceed total_tests")
            if counts["flaky_tests"] > counts["total_tests"]:
                raise ValueError("flaky_tests cannot exceed total_tests")
            records.append(ReleaseRecord(release_id=release_id, release_date=release_date, **counts, automation_duration_minutes=duration))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid row {row_number}: {exc}") from exc
    if not records:
        raise ValueError("The CSV has a header but no release rows.")
    return sorted(records, key=lambda record: (record.release_date, record.release_id))


def calculate_release_metrics(records: Iterable[ReleaseRecord]) -> list[ReleaseMetrics]:
    metrics = []
    for record in sorted(records, key=lambda item: (item.release_date, item.release_id)):
        executed = record.passed_tests + record.failed_tests
        escaped_total = record.escaped_defects + record.pre_release_defects
        metrics.append(ReleaseMetrics(
            release_id=record.release_id,
            release_date=record.release_date,
            pass_rate=record.passed_tests / executed if executed else 0.0,
            automation_coverage=record.automated_tests / record.total_tests,
            blocked_rate=record.blocked_tests / record.total_tests,
            defect_escape_rate=record.escaped_defects / escaped_total if escaped_total else 0.0,
            flaky_rate=record.flaky_tests / record.total_tests,
            escaped_defects=record.escaped_defects,
            production_incidents=record.production_incidents,
            automation_duration_minutes=record.automation_duration_minutes,
        ))
    return metrics


def aggregate_summary(records: Iterable[ReleaseRecord]) -> dict[str, float | int | str]:
    rows = list(records)
    if not rows:
        raise ValueError("At least one release is needed to calculate summary metrics.")
    metrics = calculate_release_metrics(rows)
    total_tests = sum(row.total_tests for row in rows)
    executed = sum(row.passed_tests + row.failed_tests for row in rows)
    all_defects = sum(row.escaped_defects + row.pre_release_defects for row in rows)
    duration_start = metrics[0].automation_duration_minutes
    duration_end = metrics[-1].automation_duration_minutes
    duration_change = ((duration_end - duration_start) / duration_start * 100) if duration_start else 0.0
    split = max(1, len(metrics) // 2)
    recent = metrics[-split:]
    earlier = metrics[:-split]
    recent_pass = _weighted_rate(recent, "pass_rate", [row.passed_tests + row.failed_tests for row in rows[-split:]])
    earlier_pass = _weighted_rate(earlier, "pass_rate", [row.passed_tests + row.failed_tests for row in rows[:-split]]) if earlier else recent_pass
    return {
        "release_count": len(rows),
        "pass_rate": sum(row.passed_tests for row in rows) / executed if executed else 0.0,
        "automation_coverage": sum(row.automated_tests for row in rows) / total_tests,
        "blocked_rate": sum(row.blocked_tests for row in rows) / total_tests,
        "defect_escape_rate": sum(row.escaped_defects for row in rows) / all_defects if all_defects else 0.0,
        "flaky_rate": sum(row.flaky_tests for row in rows) / total_tests,
        "escaped_defects": sum(row.escaped_defects for row in rows),
        "production_incidents": sum(row.production_incidents for row in rows),
        "average_automation_duration_minutes": sum(row.automation_duration_minutes for row in rows) / len(rows),
        "automation_duration_change_pct": duration_change,
        "recent_pass_rate": recent_pass,
        "earlier_pass_rate": earlier_pass,
        "pass_rate_change_pp": (recent_pass - earlier_pass) * 100,
        "period_start": metrics[0].release_date,
        "period_end": metrics[-1].release_date,
    }


def build_insights(summary: dict[str, float | int | str], thresholds: MetricThresholds | None = None) -> list[MetricInsight]:
    """Return evidence-backed signals; thresholds are configurable examples."""

    limits = thresholds or MetricThresholds()
    insights = []
    pass_rate = float(summary["pass_rate"])
    if pass_rate < limits.min_pass_rate:
        insights.append(MetricInsight(
            "Watch", "Execution pass rate is below the configured guide",
            f"Aggregate pass rate is {pass_rate:.1%}; configured guide is {limits.min_pass_rate:.1%}.",
            "Segment failures by service, test type, and recent changes; separate product defects from test or environment failures before setting a release gate.",
        ))
    change = float(summary["pass_rate_change_pp"])
    if change <= -3.0:
        insights.append(MetricInsight(
            "Investigate", "Recent pass rate has declined",
            f"The recent window is {abs(change):.1f} percentage points below the preceding window.",
            "Review the failing test clusters and correlate them with deployment, environment, and test-data changes.",
        ))
    coverage = float(summary["automation_coverage"])
    if coverage < limits.min_automation_coverage:
        insights.append(MetricInsight(
            "Watch", "Automation coverage is below the configured guide",
            f"Automation coverage is {coverage:.1%}; configured guide is {limits.min_automation_coverage:.1%}.",
            "Prioritize stable, high-value regression paths and track maintenance cost alongside added coverage.",
        ))
    blocked = float(summary["blocked_rate"])
    if blocked > limits.max_blocked_rate:
        insights.append(MetricInsight(
            "Investigate", "Blocked tests may be reducing execution signal",
            f"Blocked rate is {blocked:.1%}; configured guide is {limits.max_blocked_rate:.1%}.",
            "Check environment availability, test data, dependencies, and ownership for blocked scenarios.",
        ))
    escape = float(summary["defect_escape_rate"])
    if escape > limits.max_defect_escape_rate:
        insights.append(MetricInsight(
            "Investigate", "Escaped defect share is above the configured guide",
            f"Escaped defects are {escape:.1%} of recorded pre-release plus escaped defects; guide is {limits.max_defect_escape_rate:.1%}.",
            "Review escape themes and missing detection points; avoid attributing the result to an individual or team without context.",
        ))
    flaky = float(summary["flaky_rate"])
    if flaky > limits.max_flaky_rate:
        insights.append(MetricInsight(
            "Watch", "Flaky test share may be diluting confidence",
            f"Flaky tests are {flaky:.1%} of the total test inventory; guide is {limits.max_flaky_rate:.1%}.",
            "Identify repeat offenders, stabilize high-value checks, and report quarantined tests separately.",
        ))
    duration_growth = float(summary["automation_duration_change_pct"])
    if duration_growth > limits.max_duration_growth_pct:
        insights.append(MetricInsight(
            "Watch", "Automation runtime has grown over the reporting period",
            f"Runtime increased {duration_growth:.1f}% from the first to the latest release.",
            "Inspect suite composition, parallelism, environment wait time, and recent test additions before changing quality gates.",
        ))
    incidents = int(summary["production_incidents"])
    if incidents:
        insights.append(MetricInsight(
            "Review", "Production incidents occurred in the reporting period",
            f"{incidents} production incident(s) are recorded across {summary['release_count']} release(s).",
            "Use incident reviews to find systemic prevention opportunities and add targeted regression coverage.",
        ))
    if not insights:
        insights.append(MetricInsight(
            "Context", "No configured guide was exceeded in this sample",
            "This only means the selected thresholds were not crossed; it is not a certification of release quality.",
            "Continue reviewing trends, customer impact, risk, and metric definitions with the team.",
        ))
    return insights


def _weighted_rate(metrics: list[ReleaseMetrics], field: str, weights: list[int]) -> float:
    if not metrics or not weights or len(metrics) != len(weights) or sum(weights) == 0:
        return 0.0
    return sum(getattr(metric, field) * weight for metric, weight in zip(metrics, weights)) / sum(weights)

